from __future__ import annotations

import contextlib
import copy
import datetime
import logging
import threading
from collections.abc import Mapping, Generator, AsyncGenerator
from contextlib import AbstractContextManager
from typing import Optional, Any

import anyio
import anyio.to_process
import anyio.to_thread
import attrs
from tblib import pickling_support

from caqtus.device import DeviceName, DeviceConfiguration, Device
from caqtus.session import ExperimentSessionMaker, PureSequencePath
from caqtus.session.sequence import State
from caqtus.shot_compilation import (
    VariableNamespace,
    SequenceContext,
    DeviceCompiler,
    DeviceNotUsedException,
)
from caqtus.types.data import DataLabel, Data
from caqtus.types.parameter import ParameterNamespace
from .._initialize_devices import create_devices
from .._shot_handling import ShotRunner, ShotCompiler
from ..device_manager_extension import DeviceManagerExtensionProtocol

pickling_support.install()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def nothing():
    pass


@attrs.define
class ShotRetryConfig:
    """Specifies how to retry a shot if an error occurs.

    Attributes:
        exceptions_to_retry: If an exception occurs while running a shot, it will be
        retried if it is an instance of one of the exceptions in this tuple.
        number_of_attempts: The number of times to retry a shot if an error occurs.
    """

    exceptions_to_retry: tuple[type[Exception], ...] = attrs.field(
        factory=tuple,
        eq=False,
        on_setattr=attrs.setters.validate,
    )
    number_of_attempts: int = attrs.field(default=1, eq=False)


def _compile_shot(
    shot_parameters: ShotParameters, shot_compiler: ShotCompiler
) -> DeviceParameters | Exception:
    try:
        compiled = shot_compiler.compile_shot(shot_parameters.parameters)
        return DeviceParameters(
            index=shot_parameters.index,
            shot_parameters=shot_parameters.parameters,
            device_parameters=compiled,
        )
    except Exception as e:
        return e


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

        self._current_shot = 0

        # _is_shutting down is an event that is set to indicate that the background
        # tasks should stop. It can either be set by a task if an error occurs, or
        # by the __exit__ method at the end of the sequence.
        self._is_shutting_down = threading.Event()
        self._exit_stack = contextlib.AsyncExitStack()

        self._task_group = anyio.create_task_group()
        self._interruption_event = interruption_event
        self._is_watching_for_interruption = threading.Event()
        self._is_watching_for_interruption.set()

        self._device_manager_extension = device_manager_extension
        self._device_compilers: dict[DeviceName, DeviceCompiler] = {}

        self._shot_storage_sender, self._shot_storage_receiver = (
            anyio.create_memory_object_stream(4)
        )
        self._shot_parameter_sender, self._shot_parameter_receiver = (
            anyio.create_memory_object_stream[ShotParameters](4)
        )
        self._device_parameter_sender, self._device_parameter_receiver = (
            anyio.create_memory_object_stream[DeviceParameters](4)
        )

    async def run_sequence(self) -> None:
        self._prepare_sequence()
        try:
            async with self._exit_stack, self._task_group:
                devices_in_use = await self._exit_stack.enter_async_context(
                    self._create_devices_in_use()
                )
                shot_runner = self._create_shot_runner(devices_in_use)
                shot_compiler = self._create_shot_compiler(devices_in_use)
                self._set_sequence_state(State.RUNNING)
                await self._run(shot_runner, shot_compiler)
        except* SequenceInterruptedException:
            self._set_sequence_state(State.INTERRUPTED)
            raise
        except* BaseException:
            self._set_sequence_state(State.CRASHED)
            raise
        else:
            self._set_sequence_state(State.FINISHED)

    async def _run(self, shot_runner: ShotRunner, shot_compiler: ShotCompiler) -> None:
        async with anyio.create_task_group() as tg:
            tg.start_soon(self._watch_for_interruption)
            tg.start_soon(self._store_shots)
            async with self._device_parameter_receiver, self._device_parameter_sender:
                for _ in range(4):
                    self._task_group.start_soon(
                        self._compile_shots,
                        shot_compiler,
                        self._shot_parameter_receiver.clone(),
                        self._device_parameter_sender.clone(),
                    )
            self._task_group.start_soon(self._run_shots, shot_runner)

    @contextlib.asynccontextmanager
    async def _create_devices_in_use(
        self,
    ) -> AsyncGenerator[dict[DeviceName, Device], None]:
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
        shot_parameters = ShotParameters(
            index=self._current_shot, parameters=shot_variables
        )

        await self._shot_parameter_sender.send(shot_parameters)
        self._current_shot += 1

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
        while True:
            if self._interruption_event.is_set():
                raise SequenceInterruptedException(
                    f"Sequence '{self._sequence_path}' received an external "
                    f"interruption signal."
                )
            await anyio.sleep(20e-3)

    async def _compile_shots(self, shot_compiler: ShotCompiler, receiver, sender):
        async with receiver, sender:
            async for shot_parameters in receiver:
                result = await anyio.to_process.run_sync(
                    _compile_shot, shot_parameters, shot_compiler
                )
                if isinstance(result, Exception):
                    raise result
                await sender.send(result)

    async def _run_shots(self, shot_runner: ShotRunner):
        async with self._device_parameter_receiver as receiver:
            async for device_parameters in receiver:
                shot_data = await self._run_shot_with_retry(
                    device_parameters, shot_runner
                )
                await self._shot_storage_sender.send(shot_data)

    async def _run_shot_with_retry(
        self, device_parameters: DeviceParameters, shot_runner: ShotRunner
    ) -> ShotData:
        exceptions_to_retry = self._shot_retry_config.exceptions_to_retry
        number_of_attempts = self._shot_retry_config.number_of_attempts
        if number_of_attempts < 1:
            raise ValueError("number_of_attempts must be >= 1")

        errors: list[Exception] = []

        for attempt in range(number_of_attempts):
            try:
                start_time = datetime.datetime.now(tz=datetime.timezone.utc)
                data = await shot_runner.run_shot(
                    device_parameters.device_parameters, 5
                )
                end_time = datetime.datetime.now(tz=datetime.timezone.utc)
            except* exceptions_to_retry as e:
                errors.extend(e.exceptions)
                logger.warning(
                    f"Attempt {attempt+1}/{number_of_attempts} failed", exc_info=e
                )
            else:
                return ShotData(
                    index=device_parameters.index,
                    start_time=start_time,
                    end_time=end_time,
                    variables=device_parameters.shot_parameters,
                    data=data,
                )
        raise ExceptionGroup(
            f"Could not execute shot after {number_of_attempts} attempts", errors
        )

    async def _store_shots(self) -> None:
        async with self._shot_storage_receiver as receiver:
            async for shot_data in receiver:
                await anyio.to_thread.run_sync(self._store_shot, shot_data)

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


@attrs.frozen(order=True)
class ShotParameters:
    """Holds information necessary to compile a shot."""

    index: int
    parameters: VariableNamespace = attrs.field(eq=False)


@attrs.frozen(order=True)
class DeviceParameters:
    """Holds information necessary to run a shot."""

    index: int
    shot_parameters: VariableNamespace = attrs.field(eq=False)
    device_parameters: Mapping[DeviceName, Mapping[str, Any]] = attrs.field(eq=False)


@attrs.frozen(order=True)
class ShotData:
    """Holds information necessary to store a shot."""

    index: int
    start_time: datetime.datetime = attrs.field(eq=False)
    end_time: datetime.datetime = attrs.field(eq=False)
    variables: VariableNamespace = attrs.field(eq=False)
    data: Mapping[DataLabel, Data] = attrs.field(eq=False)


class SequenceInterruptedException(RuntimeError):
    pass


class LockedEvent:
    def __init__(self):
        self._event = threading.Event()
        self._lock = threading.Lock()

    def set(self):
        with self._lock:
            self._event.set()

    def clear(self):
        with self._lock:
            self._event.clear()

    def is_set(self) -> bool:
        return self._event.is_set()

    @contextlib.contextmanager
    def is_set_context(self) -> Generator[bool, None, None]:
        with self._lock:
            yield self._event.is_set()


class ProcessingFinishedException(Exception):
    pass
