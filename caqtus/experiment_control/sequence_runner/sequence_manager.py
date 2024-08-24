from __future__ import annotations

import contextlib
import copy
import logging
import threading
from collections.abc import Mapping, AsyncGenerator, AsyncIterable
from typing import Optional

import anyio
import anyio.to_process
import anyio.to_thread

from caqtus.device import DeviceName, DeviceConfiguration
from caqtus.session import (
    ExperimentSessionMaker,
    PureSequencePath,
    State,
    TracebackSummary,
)
from caqtus.shot_compilation import (
    DeviceCompiler,
    SequenceContext,
)
from caqtus.types.parameter import ParameterNamespace
from caqtus.types.recoverable_exceptions import (
    SequenceInterruptedException,
    split_recoverable,
)
from .shots_manager import ShotManager, ShotData, ShotScheduler
from .shots_manager import ShotRetryConfig
from ..device_manager_extension import DeviceManagerExtensionProtocol
from ..initialize_resources import create_shot_runner, create_shot_compiler

logger = logging.getLogger(__name__)


class SequenceManager:
    """Manages the execution of a sequence.

    Args:
        sequence: The sequence to run.
        session_maker: A factory for creating experiment sessions.
        This is used to connect to the storage in which to find the sequence.
        interruption_event: An event that is set to interrupt the sequence.
        When this event is set, the sequence manager will attempt to stop the sequence
        as soon as possible.
        Note that the sequence manager cannot interrupt a shot that is currently
        running, but will wait for it to finish.
        shot_retry_config: Specifies how to retry a shot if an error occurs.
        If an error occurs when the shot runner is running a shot, it will be caught
        by the sequence manager and the shot will be retried according to the
        configuration in this object.
        device_configurations: The device configurations to use to
        run the sequence.
        If None, the sequence manager will use the default device configurations.
    """

    def __init__(
        self,
        sequence: PureSequencePath,
        session_maker: ExperimentSessionMaker,
        interruption_event: threading.Event,
        shot_retry_config: Optional[ShotRetryConfig],
        global_parameters: Optional[ParameterNamespace],
        device_configurations: Optional[Mapping[DeviceName, DeviceConfiguration]],
        device_manager_extension: DeviceManagerExtensionProtocol,
    ) -> None:
        self._session_maker = session_maker
        self._sequence_path = sequence
        self._shot_retry_config = shot_retry_config or ShotRetryConfig()

        with self._session_maker() as session:
            if device_configurations is None:
                self.device_configurations = dict(session.default_device_configurations)
            else:
                self.device_configurations = dict(device_configurations)
            if global_parameters is None:
                self.sequence_parameters = session.get_global_parameters()
            else:
                self.sequence_parameters = copy.deepcopy(global_parameters)
            self.time_lanes = session.sequences.get_time_lanes(self._sequence_path)

        self._interruption_event = interruption_event

        self._device_manager_extension = device_manager_extension
        self._device_compilers: dict[DeviceName, DeviceCompiler] = {}

        self._watch_for_interruption_scope = anyio.CancelScope()

    @contextlib.asynccontextmanager
    async def run_sequence(self) -> AsyncGenerator[ShotScheduler, None]:
        """Run background tasks to compile and run shots for a given sequence.

        Returns:
            A asynchronous context manager that yields a shot scheduler object.

            When the context manager is entered, it will set the sequence to PREPARING
            while acquiring the necessary resources and the transition to RUNNING.

            The context manager will yield a shot scheduler object that can be used to
            push shots to the sequence execution queue.
            When a shot is done, its associated data will be stored in the associated
            sequence.

            One shot scheduling is over, the context manager will be exited.
            At this point is will finish the sequence and transition the sequence state
            to FINISHED when the sequence terminated normally, CRASHED if an error
            occurred or INTERRUPTED if the sequence was interrupted by the user.
        """

        self._prepare_sequence()
        try:
            shot_compiler = create_shot_compiler(
                SequenceContext(
                    device_configurations=self.device_configurations,
                    time_lanes=self.time_lanes,
                ),
                self._device_manager_extension,
            )
            async with (
                create_shot_runner(
                    shot_compiler, self._device_manager_extension
                ) as shot_runner,
                ShotManager(shot_runner, shot_compiler, self._shot_retry_config) as (
                    scheduler_cm,
                    data_stream_cm,
                ),
            ):
                self._set_sequence_state(State.RUNNING)
                async with (
                    anyio.create_task_group() as tg,
                    scheduler_cm as scheduler,
                ):
                    tg.start_soon(self._watch_for_interruption)
                    tg.start_soon(self._store_shots, data_stream_cm)
                    yield scheduler
        except* SequenceInterruptedException:
            self._set_sequence_state(State.INTERRUPTED)
        except* BaseException as e:
            self._set_sequence_state(State.CRASHED)
            recoverable, non_recoverable = split_recoverable(e)
            if non_recoverable:
                raise
            if recoverable:
                logger.warning(
                    "A recoverable error occurred while running the sequence.",
                    exc_info=recoverable,
                )
                traceback_summary = TracebackSummary.from_exception(recoverable)
                with self._session_maker() as session:
                    session.sequences.set_exception(
                        self._sequence_path, traceback_summary
                    )
        else:
            self._set_sequence_state(State.FINISHED)

    def _prepare_sequence(self):
        with self._session_maker() as session:
            session.sequences.set_state(self._sequence_path, State.PREPARING)
            session.sequences.set_device_configurations(
                self._sequence_path, self.device_configurations
            )
            session.sequences.set_global_parameters(
                self._sequence_path, self.sequence_parameters
            )

    def _set_sequence_state(self, state: State):
        with self._session_maker() as session:
            session.sequences.set_state(self._sequence_path, state)

    async def _watch_for_interruption(self):
        with self._watch_for_interruption_scope:
            while True:
                if self._interruption_event.is_set():
                    raise SequenceInterruptedException(
                        f"Sequence '{self._sequence_path}' received an external "
                        f"interruption signal."
                    )
                await anyio.sleep(20e-3)

    async def _store_shots(
        self,
        data_stream_cm: contextlib.AbstractAsyncContextManager[AsyncIterable[ShotData]],
    ):
        async with data_stream_cm as shots_data:
            async for shot_data in shots_data:
                self._store_shot(shot_data)
        self._watch_for_interruption_scope.cancel()

    def _store_shot(self, shot_data: ShotData) -> None:
        params = {
            name: value for name, value in shot_data.variables.to_flat_dict().items()
        }
        with self._session_maker() as session:
            session.sequences.create_shot(
                self._sequence_path,
                shot_data.index,
                params,
                shot_data.data,
                shot_data.start_time,
                shot_data.end_time,
            )
