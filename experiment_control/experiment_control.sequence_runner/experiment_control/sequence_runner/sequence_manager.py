import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractContextManager, ExitStack
from queue import PriorityQueue, Empty
from threading import Event
from typing import Self, Any, Optional

from attr import frozen, field

from device.configuration import DeviceParameter
from device.name import DeviceName
from device.runtime import RuntimeDevice
from duration_timer import DurationTimerLog
from experiment.configuration import ExperimentConfig
from experiment.session import ExperimentSessionMaker
from experiment_control.compute_device_parameters import (
    get_devices_initialization_parameters,
    compute_parameters_on_variables_update,
    compute_shot_parameters,
)
from sequence.configuration import SequenceConfig
from sequence.runtime import SequencePath, Sequence, State
from .device_servers import (
    create_device_servers,
    connect_to_device_servers,
    create_devices,
)
from .devices_handler import DevicesHandler
from .sequence_context import StepContext

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@frozen(order=True)
class ShotParameters:
    """Holds information necessary to compile a shot."""

    name: str
    index: int
    context: StepContext = field(eq=False)


@frozen(order=True)
class ShotDeviceParameters:
    """Holds information necessary to execute a shot.

    Args:
        name: The name of the shot.
        index: The index of the shot.
        context: The context of the step that must be executed.
        change_parameters: The parameters that needs to be changed do to a variable having changed between shots, as
        computed by compute_parameters_on_variables_update. If no variable changed, this will be an empty dict.
        static_parameters: The parameters that need to be set for the shot, as computed by compute_shot_parameters. Even
        if no variable changed, this will be a non-empty dict.
    """

    name: str
    index: int
    context: StepContext = field(eq=False)
    change_parameters: dict[DeviceName, dict[DeviceParameter, Any]] = field(eq=False)
    static_parameters: dict[DeviceName, dict[DeviceParameter, Any]] = field(eq=False)


class SequenceManager(AbstractContextManager):
    def __init__(
        self,
        experiment_config_name: str,
        sequence_path: SequencePath,
        session_maker: ExperimentSessionMaker,
        max_schedulable_shots: Optional[int] = 10,
    ) -> None:
        self._experiment_config_name = experiment_config_name
        self._experiment_config: ExperimentConfig
        self._sequence = Sequence(sequence_path)
        self._sequence_config: SequenceConfig
        self._session_maker = session_maker

        self._exit_stack = ExitStack()
        self._thread_pool = ThreadPoolExecutor()
        self._asked_to_interrupt = False
        self._stop_background_tasks = Event()

        self._device_manager: DevicesHandler

        if max_schedulable_shots is None:
            max_schedulable_shots = 0
        self._shot_parameters_queue = PriorityQueue[ShotParameters](
            max_schedulable_shots
        )
        self._current_shot = 0

    @property
    def experiment_config(self) -> ExperimentConfig:
        return self._experiment_config

    @property
    def sequence_config(self) -> SequenceConfig:
        return self._sequence_config

    def schedule_shot(self, shot_name: str, shot_context: StepContext) -> None:
        if self.asked_to_interrupt():
            raise SequenceInterruptedError(
                "Cannot schedule a shot after the sequence was interrupted."
            )
        self._shot_parameters_queue.put(
            ShotParameters(
                name=shot_name, index=self._current_shot, context=shot_context
            )
        )
        self._current_shot += 1

    def __enter__(self) -> Self:
        with self._session_maker() as session:
            self._sequence.set_experiment_config(self._experiment_config_name, session)
            self._sequence.set_state(State.PREPARING, session)
        try:
            self._prepare()
            self._set_sequence_state(State.RUNNING)
        except Exception:
            self._set_sequence_state(State.CRASHED)
            raise
        return self

    def _prepare(self) -> None:
        self._exit_stack.__enter__()
        self._exit_stack.enter_context(self._thread_pool)
        self._thread_pool.submit(self._consume_shot_parameters)
        with self._session_maker() as session:
            self._experiment_config = session.experiment_configs[
                self._experiment_config_name
            ]
            self._sequence_config = self._sequence.get_config(session)

        devices = self._create_uninitialized_devices()
        self._device_manager = DevicesHandler(devices)
        self._exit_stack.enter_context(self._device_manager)

    def _create_uninitialized_devices(self) -> dict[DeviceName, RuntimeDevice]:
        """Create the devices on their respective servers.

        The devices are created with the initial parameters specified in the experiment and sequence configs, but the
        connection to the devices is not established. The device objects are proxies to the actual devices that are
        running in other processes, possibly on other computers.
        """

        remote_device_servers = create_device_servers(
            self._experiment_config.device_servers
        )
        connect_to_device_servers(remote_device_servers)

        initialization_parameters = get_devices_initialization_parameters(
            self._experiment_config, self._sequence_config
        )
        devices = create_devices(
            initialization_parameters,
            remote_device_servers,
            self._experiment_config.mock_experiment,
        )
        return devices

    def _consume_shot_parameters(self) -> None:
        while not self._stop_background_tasks.is_set():
            try:
                shot_parameters = self._shot_parameters_queue.get(timeout=10e-3)
            except Empty:
                continue
            else:
                with DurationTimerLog(logger, "Computing shot parameters"):
                    devices_shot_parameters = self.compute_shot_parameters(
                        shot_parameters
                    )
                self._shot_parameters_queue.task_done()

    def compute_shot_parameters(
        self, shot_parameters: ShotParameters
    ) -> ShotDeviceParameters:
        change_params = compute_parameters_on_variables_update(
            shot_parameters.context.updated_variables,
            shot_parameters.context.variables,
            self.experiment_config,
        )
        shot_params = compute_shot_parameters(
            self.experiment_config,
            self._sequence_config.shot_configurations[shot_parameters.name],
            shot_parameters.context.variables,
        )

        return ShotDeviceParameters(
            name=shot_parameters.name,
            context=shot_parameters.context,
            index=shot_parameters.index,
            change_parameters=change_params,
            static_parameters=shot_params,
        )

    def __exit__(self, exc_type, exc_value, traceback):
        error_occurred = exc_value is not None
        try:
            if error_occurred or self.asked_to_interrupt():
                self._thread_pool.shutdown(cancel_futures=True)
            else:
                self._shot_parameters_queue.join()
            self._stop_background_tasks.set()
            self._exit_stack.__exit__(exc_type, exc_value, traceback)
        except Exception:
            self._set_sequence_state(State.CRASHED)
            raise
        else:
            if error_occurred:
                if isinstance(exc_value, SequenceInterruptedError):
                    self._set_sequence_state(State.INTERRUPTED)
                    return True
                else:
                    self._set_sequence_state(State.CRASHED)
                    return False
            elif self.asked_to_interrupt():
                self._set_sequence_state(State.INTERRUPTED)
            else:
                self._set_sequence_state(State.FINISHED)

    def interrupt_sequence(self) -> None:
        self._asked_to_interrupt = True
        self._stop_background_tasks.set()

    def asked_to_interrupt(self) -> bool:
        return self._asked_to_interrupt

    def _set_sequence_state(self, state: State):
        with self._session_maker() as session:
            self._sequence.set_state(state, session)


class SequenceInterruptedError(RuntimeError):
    pass
