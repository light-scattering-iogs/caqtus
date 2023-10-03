from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractContextManager, ExitStack
from threading import Event
from typing import Self

from device.name import DeviceName
from device.runtime import RuntimeDevice
from experiment.configuration import ExperimentConfig
from experiment.session import ExperimentSessionMaker
from experiment_control.compute_device_parameters import (
    get_devices_initialization_parameters,
)
from sequence.configuration import SequenceConfig
from sequence.runtime import SequencePath, Sequence, State
from .device_servers import (
    create_device_servers,
    connect_to_device_servers,
    create_devices,
)
from .devices_handler import DevicesHandler


class SequenceManager(AbstractContextManager):
    def __init__(
        self,
        experiment_config_name: str,
        sequence_path: SequencePath,
        session_maker: ExperimentSessionMaker,
    ) -> None:
        self._experiment_config_name = experiment_config_name
        self._experiment_config: ExperimentConfig
        self._sequence = Sequence(sequence_path)
        self._sequence_config: SequenceConfig
        self._session_maker = session_maker

        self._exit_stack = ExitStack()
        self._thread_pool = ThreadPoolExecutor()
        self._must_interrupt = Event()

        self._device_manager: DevicesHandler

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

    def __exit__(self, exc_type, exc_value, traceback):
        error_occurred = exc_value is not None
        try:
            if error_occurred or self.asked_to_interrupt():
                self._thread_pool.shutdown(cancel_futures=True)
            self._exit_stack.__exit__(exc_type, exc_value, traceback)
        except Exception:
            self._set_sequence_state(State.CRASHED)
            raise
        else:
            if error_occurred:
                self._set_sequence_state(State.CRASHED)
            else:
                if self.asked_to_interrupt():
                    self._set_sequence_state(State.INTERRUPTED)
                else:
                    self._set_sequence_state(State.FINISHED)

    def interrupt_sequence(self) -> None:
        self._must_interrupt.set()

    def asked_to_interrupt(self) -> bool:
        return self._must_interrupt.is_set()

    def _set_sequence_state(self, state: State):
        with self._session_maker() as session:
            self._sequence.set_state(state, session)
