from __future__ import annotations

import concurrent.futures
import contextlib
import copy
import datetime
import logging
import queue
import threading
from collections.abc import Mapping, Generator
from contextlib import AbstractContextManager
from typing import Optional, Any

import attrs
from tblib import pickling_support

from caqtus.device import DeviceName, DeviceConfiguration
from caqtus.device.remote_server import DeviceServerConfiguration, RemoteDeviceManager
from caqtus.session import ExperimentSessionMaker, Sequence, ParameterNamespace
from caqtus.session.sequence import State
from caqtus.shot_compilation import VariableNamespace, ShotCompiler, SequenceContext
from caqtus.types.data import DataLabel, Data
from caqtus.utils.concurrent import TaskGroup
from .._shot_handling import ShotRunner
from ..initialize_devices import create_devices

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


class SequenceManager(AbstractContextManager):
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
        sequence: Sequence,
        session_maker: ExperimentSessionMaker,
        interruption_event: threading.Event,
        device_server_configs: Mapping[str, DeviceServerConfiguration],
        manager_class: type[RemoteDeviceManager],
        shot_retry_config: Optional[ShotRetryConfig],
        global_parameters: Optional[ParameterNamespace],
        device_configurations: Optional[Mapping[DeviceName, DeviceConfiguration]],
    ) -> None:
        self._session_maker = session_maker
        self._sequence_path = sequence.path
        self._shot_retry_config = shot_retry_config or ShotRetryConfig()
        self.device_server_configs = device_server_configs
        self.manager_class = manager_class

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
        self._exit_stack = contextlib.ExitStack()
        self._thread_pool = concurrent.futures.ThreadPoolExecutor()
        self._process_pool = concurrent.futures.ProcessPoolExecutor()

        self._shot_parameter_queue = queue.PriorityQueue[ShotParameters](4)
        self._is_compiling = LockedEvent()
        self._is_compiling.set()

        self._device_parameter_queue = queue.PriorityQueue[DeviceParameters](4)
        self._is_running_shots = LockedEvent()
        self._is_running_shots.set()

        self._shot_data_queue = queue.PriorityQueue[ShotData](4)
        self._is_saving_data = LockedEvent()
        self._is_saving_data.set()

        self._task_group = TaskGroup(
            self._thread_pool, name=f"managing the sequence '{self._sequence_path}'"
        )
        self._interruption_event = interruption_event
        self._is_watching_for_interruption = threading.Event()
        self._is_watching_for_interruption.set()

    def __enter__(self):
        self._prepare_sequence()
        self._exit_stack.__enter__()
        try:
            self._prepare()
            self._set_sequence_state(State.RUNNING)
        except Exception as e:
            self._exit_stack.__exit__(type(e), e, e.__traceback__)
            self._set_sequence_state(State.CRASHED)
            raise
        return self

    def _prepare(self) -> None:
        self._exit_stack.enter_context(self._process_pool)
        # This task is here to force the process pool to start now.
        # Otherwise, it waits until the first shot is submitted for compilation.
        task = self._process_pool.submit(nothing)
        self._exit_stack.enter_context(self._thread_pool)

        devices_in_use = self._create_devices_in_use()

        shot_runner = self._create_shot_runner(devices_in_use)
        self._exit_stack.enter_context(shot_runner)

        self._task_group.__enter__()
        self._task_group.create_task(self._watch_for_interruption)
        self._task_group.create_task(self._store_shots)
        shot_compiler = self._create_shot_compiler(devices_in_use)
        for _ in range(4):
            self._task_group.create_task(self._compile_shots, shot_compiler)
        self._task_group.create_task(self._run_shots, shot_runner)
        task.result()

    def _create_devices_in_use(self):
        sequence_context = SequenceContext(
            device_configurations=self.device_configurations, time_lanes=self.time_lanes
        )
        devices_in_use = create_devices(
            self.device_configurations,
            self.device_server_configs,
            self.manager_class,
            sequence_context,
        )
        return devices_in_use

    def _create_shot_runner(self, devices_in_use) -> ShotRunner:
        device_controller_types = {
            name: self.device_configurations[name].get_controller_type()
            for name in devices_in_use
        }
        shot_runner = ShotRunner(devices_in_use, device_controller_types)
        return shot_runner

    def _create_shot_compiler(self, devices_in_use) -> ShotCompiler:
        shot_compiler = ShotCompiler(
            self.time_lanes,
            {name: self.device_configurations[name] for name in devices_in_use},
        )
        return shot_compiler

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Indicates if an error occurred in the scheduler thread.
        error_occurred = exc_val is not None
        if error_occurred:
            self._is_compiling.clear()
            self._is_running_shots.clear()
            self._is_saving_data.clear()

        self._shot_parameter_queue.join()
        self._is_compiling.clear()
        self._device_parameter_queue.join()
        self._is_running_shots.clear()
        self._shot_data_queue.join()
        self._is_saving_data.clear()
        self._is_watching_for_interruption.clear()
        try:
            # Here we check is any of the background tasks raised an exception. If so,
            # they are re-raised here, and the exception that occurred in the scheduler
            # thread is added to the list of exceptions.
            try:
                self._task_group.__exit__(exc_type, exc_val, exc_tb)
            except ExceptionGroup as e:
                if error_occurred:
                    raise ExceptionGroup(e.message, [*e.exceptions, exc_val])
                else:
                    raise e
            else:
                if error_occurred:
                    raise exc_val
        except* SequenceInterruptedException:
            state = State.INTERRUPTED
            raise
        except* Exception:
            state = State.CRASHED
            raise
        else:
            state = State.FINISHED
        finally:
            try:
                self._set_sequence_state(state)
            finally:
                self._exit_stack.__exit__(exc_type, exc_val, exc_tb)

    def schedule_shot(self, shot_variables: VariableNamespace) -> None:
        shot_parameters = ShotParameters(
            index=self._current_shot, parameters=shot_variables
        )

        def try_pushing_shot() -> bool:
            with self._is_compiling.is_set_context() as is_compiling:
                if not is_compiling:
                    if self._interruption_event.is_set():
                        raise SequenceInterruptedException(
                            f"Cannot schedule shot after sequence has been "
                            f"interrupted."
                        )
                    else:
                        raise RuntimeError(
                            "Cannot schedule shot after shot compilation has been "
                            "terminated."
                        )
                try:
                    self._shot_parameter_queue.put(shot_parameters, timeout=20e-3)
                except queue.Full:
                    return False
                else:
                    return True

        while not try_pushing_shot():
            continue
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

    def _watch_for_interruption(self):
        while self._is_watching_for_interruption.is_set():
            if self._interruption_event.wait(20e-3):
                logger.debug("Sequence interrupted")
                self._is_compiling.clear()
                self._is_running_shots.clear()
                self._is_saving_data.clear()
                raise SequenceInterruptedException(
                    f"Sequence '{self._sequence_path}' received an external "
                    f"interruption signal."
                )
            else:
                continue

    def _compile_shots(self, shot_compiler: ShotCompiler):
        try:
            while self._is_compiling.is_set():
                try:
                    shot_parameters = self._shot_parameter_queue.get(timeout=20e-3)
                except queue.Empty:
                    continue
                try:
                    task = self._process_pool.submit(
                        _compile_shot, shot_parameters, shot_compiler
                    )
                    result = task.result()
                    # Here we don't use task.exception() because it returns an ugly
                    # RemoteTraceback that is hard to read.
                    # Instead, if an exception occurs in the task, it is pickled with
                    # tblib and returned, so we just have to check if the result is an
                    # exception or not.
                    if isinstance(result, Exception):
                        result.add_note(f"When compiling shot {shot_parameters.index}")
                        raise result
                    self.put_device_parameters(result)
                except ProcessingFinishedException:
                    self._is_compiling.clear()
                    break
                except Exception:
                    self._is_compiling.clear()
                    raise
                finally:
                    self._shot_parameter_queue.task_done()
        finally:
            discard_queue(self._shot_parameter_queue)

    def put_device_parameters(self, device_parameters: DeviceParameters) -> None:
        while True:
            with self._is_running_shots.is_set_context() as is_processing:
                if not is_processing:
                    raise ProcessingFinishedException(
                        "Cannot put device parameters after processing has been "
                        "terminated."
                    )
                try:
                    self._device_parameter_queue.put(device_parameters, timeout=20e-3)
                    return
                except queue.Full:
                    continue

    def _run_shots(self, shot_runner: ShotRunner):
        try:
            while self._is_running_shots.is_set():
                try:
                    device_parameters = self._device_parameter_queue.get(timeout=20e-3)
                except queue.Empty:
                    continue
                try:
                    shot_data = self._run_shot_with_retry(
                        device_parameters, shot_runner
                    )
                    self.put_shot_data(shot_data)
                except ProcessingFinishedException:
                    self._is_running_shots.clear()
                    break
                except Exception:
                    self._is_running_shots.clear()
                    raise
                finally:
                    self._device_parameter_queue.task_done()
        finally:
            discard_queue(self._device_parameter_queue)

    def put_shot_data(self, shot_data: ShotData) -> None:
        while True:
            with self._is_saving_data.is_set_context() as is_saving:
                if not is_saving:
                    raise ProcessingFinishedException(
                        "Cannot put shot data after saving has been terminated."
                    )
                try:
                    self._shot_data_queue.put(shot_data, timeout=20e-3)
                    return
                except queue.Full:
                    continue

    def _run_shot_with_retry(
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
                data = shot_runner.run_shot(device_parameters.device_parameters, 5)
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

    def _store_shots(self):
        try:
            while self._is_saving_data.is_set():
                try:
                    shot_data = self._shot_data_queue.get(timeout=20e-3)
                except queue.Empty:
                    continue
                try:
                    self._store_shot(shot_data)
                except Exception:
                    self._is_saving_data.clear()
                    raise
                finally:
                    self._shot_data_queue.task_done()
        finally:
            discard_queue(self._shot_data_queue)

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


def discard_queue(q: queue.Queue) -> None:
    while True:
        try:
            q.get_nowait()
            q.task_done()
        except queue.Empty:
            break


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
