from __future__ import annotations

import contextlib
import copy
import logging
from collections.abc import Mapping, AsyncGenerator, AsyncIterable
from typing import Optional

import anyio

from caqtus.device import DeviceName, DeviceConfiguration
from caqtus.session import (
    ExperimentSessionMaker,
    PureSequencePath,
    State,
    TracebackSummary,
    ExperimentSession,
)
from caqtus.session._shot_id import ShotId
from caqtus.shot_compilation import (
    DeviceCompiler,
    SequenceContext,
)
from caqtus.types.iteration import StepsConfiguration
from caqtus.types.parameter import ParameterNamespace
from caqtus.types.recoverable_exceptions import split_recoverable
from caqtus.utils._result import unwrap
from ._shot_compiler import ShotCompilerFactory, create_shot_compiler
from ._shot_runner import ShotRunnerFactory, create_shot_runner
from .sequence_runner import execute_steps, evaluate_initial_context
from .shots_manager import ShotManager, ShotData, ShotScheduler, ShotRetryConfig
from ..device_manager_extension import DeviceManagerExtensionProtocol

logger = logging.getLogger(__name__)


async def run_sequence(
    sequence: PureSequencePath,
    session_maker: ExperimentSessionMaker,
    shot_retry_config: Optional[ShotRetryConfig],
    global_parameters: Optional[ParameterNamespace],
    device_configurations: Optional[Mapping[DeviceName, DeviceConfiguration]],
    device_manager_extension: DeviceManagerExtensionProtocol,
    shot_runner_factory: ShotRunnerFactory = create_shot_runner,
    shot_compiler_factory: ShotCompilerFactory = create_shot_compiler,
) -> None:
    """Manages the execution of a sequence.

    Args:
        sequence: The sequence to run.

        session_maker: A factory for creating experiment sessions.
            This is used to connect to the storage in which to find the sequence.

        shot_retry_config: Specifies how to retry a shot if an error occurs.
            If an error occurs when the shot runner is running a shot, it will be caught
            by the sequence manager and the shot will be retried according to the
            configuration in this object.

        global_parameters: The global parameters to use to run the sequence.

            These parameters will be saved as the global parameters for the sequence
            when it is prepared.

            If None, the sequence manager will use the default global parameters stored
            in the session.

        device_configurations: The device configurations to use to run the sequence.

            These configurations will be saved as the configurations used for the
            sequence when it is prepared.

            If None, the sequence manager will use the default device configurations.

        device_manager_extension: Used to instantiate the device components.

        shot_runner_factory: A function that can be used to create an object to run
            shots.

        shot_compiler_factory: A function that can be used to create an object to
            compile shots.
    """

    with session_maker.session() as session:
        iteration = session.sequences.get_iteration_configuration(sequence)
    if not isinstance(iteration, StepsConfiguration):
        raise NotImplementedError("Only steps iteration is supported at the moment.")
    sequence_manager = SequenceManager(
        sequence=sequence,
        session_maker=session_maker,
        shot_retry_config=shot_retry_config,
        global_parameters=global_parameters,
        device_configurations=device_configurations,
        device_manager_extension=device_manager_extension,
        shot_runner_factory=shot_runner_factory,
        shot_compiler_factory=shot_compiler_factory,
    )
    initial_context = evaluate_initial_context(sequence_manager.sequence_parameters)
    async with sequence_manager.run_sequence() as shot_scheduler:
        await execute_steps(iteration.steps, initial_context, shot_scheduler)


class SequenceManager:
    def __init__(
        self,
        sequence: PureSequencePath,
        session_maker: ExperimentSessionMaker,
        shot_retry_config: Optional[ShotRetryConfig],
        global_parameters: Optional[ParameterNamespace],
        device_configurations: Optional[Mapping[DeviceName, DeviceConfiguration]],
        device_manager_extension: DeviceManagerExtensionProtocol,
        shot_runner_factory: ShotRunnerFactory,
        shot_compiler_factory: ShotCompilerFactory,
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

        self._device_manager_extension = device_manager_extension
        self._device_compilers: dict[DeviceName, DeviceCompiler] = {}

        self._shot_runner_factory = shot_runner_factory
        self._shot_compiler_factory = shot_compiler_factory

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
            sequence_context = SequenceContext(
                device_configurations=self.device_configurations,  # pyright: ignore[reportCallIssue]
                time_lanes=self.time_lanes,  # pyright: ignore[reportCallIssue]
            )
            shot_compiler = self._shot_compiler_factory(
                sequence_context,
                self._device_manager_extension,
            )
            async with (
                self._shot_runner_factory(
                    sequence_context, shot_compiler, self._device_manager_extension
                ) as shot_runner,
                ShotManager(
                    shot_runner,
                    shot_compiler,
                    self._shot_retry_config,
                ) as (
                    scheduler_cm,
                    data_stream_cm,
                ),
            ):
                self._set_sequence_state(State.RUNNING)
                async with (
                    anyio.create_task_group() as tg,
                    scheduler_cm as scheduler,
                ):
                    tg.start_soon(self._store_shots, data_stream_cm)
                    yield scheduler
        except* anyio.get_cancelled_exc_class():
            self._set_sequence_state(State.INTERRUPTED)
            raise
        except* BaseException as e:
            self._set_sequence_state(State.CRASHED)
            traceback_summary = TracebackSummary.from_exception(e)
            with self._session_maker() as session:
                unwrap(
                    session.sequences.set_exception(
                        self._sequence_path, traceback_summary
                    )
                )
            recoverable, non_recoverable = split_recoverable(e)
            if non_recoverable:
                raise
            if recoverable:
                logger.warning(
                    "A recoverable error occurred while running the sequence.",
                    exc_info=recoverable,
                )

        else:
            self._set_sequence_state(State.FINISHED)

    def _prepare_sequence(self):
        with self._session_maker() as session:
            _prepare_sequence(
                self._sequence_path,
                session,
                self.device_configurations,
                self.sequence_parameters,
            )

    def _set_sequence_state(self, state: State):
        with self._session_maker() as session:
            unwrap(session.sequences.set_state(self._sequence_path, state))

    async def _store_shots(
        self,
        data_stream_cm: contextlib.AbstractAsyncContextManager[AsyncIterable[ShotData]],
    ):
        async with data_stream_cm as shots_data:
            async for shot_data in shots_data:
                await self._store_shot(shot_data)

    async def _store_shot(self, shot_data: ShotData) -> None:
        params = {
            name: value for name, value in shot_data.variables.to_flat_dict().items()
        }
        async with self._session_maker.async_session() as session:
            result = await session.sequences.create_shot(
                ShotId(self._sequence_path, shot_data.index),
                params,
                shot_data.data,
                shot_data.start_time,
                shot_data.end_time,
            )
            unwrap(result)


def _prepare_sequence(
    path: PureSequencePath,
    session: ExperimentSession,
    device_configurations: Mapping[DeviceName, DeviceConfiguration],
    global_parameters: ParameterNamespace,
):
    """Transition a sequence to the preparing state.

    Args:
        path: The path to the sequence to prepare.
        session: The link to the storage in which to find the sequence.
        device_configurations: The configurations of the devices that were used to run
            this sequence.
        global_parameters: The parameters used to run the sequence.
    """

    unwrap(session.sequences.set_state(path, State.PREPARING))
    session.sequences.set_device_configurations(path, device_configurations)
    session.sequences.set_global_parameters(path, global_parameters)
