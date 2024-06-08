from __future__ import annotations

import contextlib
import copy
import logging
import threading
from collections.abc import Mapping, AsyncGenerator
from typing import Optional

import anyio
import anyio.to_process
import anyio.to_thread
from tblib import pickling_support

from caqtus.device import DeviceName, DeviceConfiguration
from caqtus.device.remote import DeviceProxy
from caqtus.session import ExperimentSessionMaker, PureSequencePath
from caqtus.session.sequence import State
from caqtus.shot_compilation import (
    VariableNamespace,
    SequenceContext,
    DeviceCompiler,
    DeviceNotUsedException,
)
from caqtus.types.parameter import ParameterNamespace
from .shots_manager import ShotManager, ShotData
from .shots_manager import ShotRetryConfig
from .._initialize_devices import create_devices
from .._shot_handling import ShotRunner, ShotCompiler
from ..device_manager_extension import DeviceManagerExtensionProtocol

pickling_support.install()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def nothing():
    pass


class SequenceManager:
    """Manages the execution of a sequence.

    Instances of this class run background tasks to compile and run shots for a given
    sequence.
    It will properly manage the state of the sequence, meaning it will set it to
    PREPARING while acquiring the necessary resources, RUNNING while running the shots,
    FINISHED when the sequence is done normally, CRASHED if an error occurs, and
    INTERRUPTED if the sequence is interrupted by the user.

    When calling :meth:`schedule_shot`, the parameters for a shot are queued for
    compilation.
    A :py:class:`ShotCompiler` will compile the shot parameters into device parameters.
    The device parameters are then queued to run a shot on the experiment.
    When a shot runs, it produces data.
    The data is then queued for storage.

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

        self._exit_stack = contextlib.AsyncExitStack()

        self._interruption_event = interruption_event

        self._device_manager_extension = device_manager_extension
        self._device_compilers: dict[DeviceName, DeviceCompiler] = {}

        self._watch_for_interruption_scope = anyio.CancelScope()
        self._shot_manager: ShotManager

    @contextlib.asynccontextmanager
    async def run_sequence(self) -> AsyncGenerator[None, None]:
        self._prepare_sequence()
        try:
            async with self._exit_stack:
                async with anyio.create_task_group() as tg:
                    # this task is present below to force the initialization of the
                    # process pool while the devices are being initialized.
                    tg.start_soon(anyio.to_process.run_sync, nothing)

                    devices_in_use = await self._exit_stack.enter_async_context(
                        self._create_devices_in_use()
                    )
                    shot_runner = self._create_shot_runner(devices_in_use)
                    shot_compiler = self._create_shot_compiler(devices_in_use)
                    self._shot_manager = ShotManager(
                        shot_runner, shot_compiler, self._shot_retry_config
                    )
                self._set_sequence_state(State.RUNNING)
                async with (
                    anyio.create_task_group() as tg,
                    self._shot_manager.start_scheduling(),
                ):
                    tg.start_soon(self._watch_for_interruption)
                    tg.start_soon(self._store_shots)
                    yield

        except* SequenceInterruptedException:
            self._set_sequence_state(State.INTERRUPTED)
            raise
        except* BaseException:
            self._set_sequence_state(State.CRASHED)
            raise
        else:
            self._set_sequence_state(State.FINISHED)

    @contextlib.asynccontextmanager
    async def _create_devices_in_use(
        self,
    ) -> AsyncGenerator[dict[DeviceName, DeviceProxy], None]:
        sequence_context = SequenceContext(
            device_configurations=self.device_configurations, time_lanes=self.time_lanes
        )
        self._device_compilers = {}
        device_types = {}
        for device_name, device_configuration in self.device_configurations.items():
            compiler_type = self._device_manager_extension.get_device_compiler_type(
                device_configuration
            )
            try:
                compiler = compiler_type(device_name, sequence_context)
            except DeviceNotUsedException:
                continue
            else:
                self._device_compilers[device_name] = compiler
                device_types[device_name] = (
                    self._device_manager_extension.get_device_type(device_configuration)
                )
        async with create_devices(
            self._device_compilers,
            self.device_configurations,
            device_types,
            self._device_manager_extension,
        ) as devices_in_use:
            yield devices_in_use

    def _create_shot_runner(self, devices_in_use) -> ShotRunner:
        device_controller_types = {
            name: self._device_manager_extension.get_device_controller_type(
                self.device_configurations[name]
            )
            for name in devices_in_use
        }
        shot_runner = ShotRunner(devices_in_use, device_controller_types)
        return shot_runner

    def _create_shot_compiler(self, devices_in_use) -> ShotCompiler:
        shot_compiler = ShotCompiler(
            self.time_lanes,
            {name: self.device_configurations[name] for name in devices_in_use},
            self._device_compilers,
        )
        return shot_compiler

    async def schedule_shot(self, shot_variables: VariableNamespace) -> None:
        await self._shot_manager.schedule_shot(shot_variables)

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

    async def _store_shots(self):
        async with self._shot_manager.run() as shots_data:
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


class SequenceInterruptedException(RuntimeError):
    pass


class ProcessingFinishedException(Exception):
    pass
