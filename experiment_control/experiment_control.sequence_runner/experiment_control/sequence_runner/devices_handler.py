import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractContextManager, ExitStack
from threading import Lock
from typing import (
    TYPE_CHECKING,
    Mapping,
    Any,
)

from aod_tweezer_arranger.configuration import AODTweezerArrangerConfiguration
from camera.configuration import CameraConfiguration
from device.configuration import DeviceName, DeviceParameter
from device.runtime import RuntimeDevice
from duration_timer import DurationTimerLog
from experiment.configuration import ExperimentConfig
from experiment_control.sequence_runner.device_context_manager import (
    DeviceContextManager,
)
from sequencer.configuration import SequencerConfiguration
from sequencer.runtime import Sequencer

if TYPE_CHECKING:
    from camera.runtime import Camera
    from aod_tweezer_arranger.runtime import AODTweezerArranger

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class DevicesHandler(AbstractContextManager):
    def __init__(
        self,
        devices: dict[DeviceName, RuntimeDevice],
        experiment_config: ExperimentConfig,
    ):
        self._devices = devices
        self._exit_stack = ExitStack()
        self._lock = Lock()

        self.sequencers = get_sequencers_in_use(devices, experiment_config)
        self.cameras = get_cameras_in_use(devices, experiment_config)
        self.tweezer_arrangers = get_tweezer_arrangers_in_use(
            devices, experiment_config
        )
        self._thread_pool = ThreadPoolExecutor(max_workers=1)

    def __enter__(self):
        self._exit_stack.__enter__()
        self._exit_stack.enter_context(self._thread_pool)
        try:
            with asyncio.Runner() as runner:
                runner.run(self._start_devices())
        except Exception:
            self._exit_stack.close()
            raise
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        return self._exit_stack.__exit__(exc_type, exc_value, exc_traceback)

    async def _start_devices(self):
        async with asyncio.TaskGroup() as g:
            for device_name, device in self._devices.items():
                g.create_task(asyncio.to_thread(self._start_device, device))

    def _start_device(self, device: RuntimeDevice):
        with self._lock:
            self._exit_stack.enter_context(DeviceContextManager(device))
        device.initialize()
        logger.info(f"Device '{device.get_name()}' initialized.")

    def update_device_parameters(
        self, device_parameters: Mapping[DeviceName, dict[DeviceParameter, Any]]
    ):
        with asyncio.Runner() as runner:
            runner.run(self._update_device_parameters(device_parameters))

    async def _update_device_parameters(
        self, device_parameters: Mapping[DeviceName, dict[DeviceParameter, Any]]
    ):
        async with asyncio.TaskGroup() as g:
            for device_name, parameters in device_parameters.items():
                g.create_task(
                    asyncio.to_thread(
                        update_device, self._devices[device_name], parameters
                    )
                )

    def start_shot(self):
        self._thread_pool.submit(asyncio.run, self._start_shot()).result()

    async def _start_shot(self):
        sequencers = list(self.sequencers.values())
        async with asyncio.TaskGroup() as g:
            for tweezer_arranger in self.tweezer_arrangers.values():
                g.create_task(asyncio.to_thread(tweezer_arranger.start_sequence))
            for camera in self.cameras.values():
                g.create_task(asyncio.to_thread(camera.start_acquisition))
            for sequencer in sequencers[:-1]:
                g.create_task(asyncio.to_thread(sequencer.start_sequence))

        # We start the sequencer with the lower priority last so that it can trigger the other sequencers.
        sequencers[-1].start_sequence()

    def finish_shot(self):
        for tweezer_arranger in self.tweezer_arrangers.values():
            tweezer_arranger.save_awg_data()


def get_sequencers_in_use(
    devices: Mapping[DeviceName, RuntimeDevice], experiment_config: ExperimentConfig
) -> dict[DeviceName, Sequencer]:
    """Return the sequencer devices used in the experiment.

    The sequencers are sorted by trigger priority, with the highest priority first.
    """

    # Here we can't test the type of the runtime device itself because it is actually a proxy and not an instance of
    # the actual device class, that's why we need to test the type of the configuration instead.
    sequencers: dict[DeviceName, Sequencer] = {
        device_name: device
        for device_name, device in devices.items()
        if isinstance(
            experiment_config.get_device_config(device_name),
            SequencerConfiguration,
        )
    }
    sorted_by_trigger_priority = sorted(
        sequencers.items(), key=lambda x: x[1].get_trigger_priority(), reverse=True
    )
    return dict(sorted_by_trigger_priority)


def get_cameras_in_use(
    devices: Mapping[DeviceName, RuntimeDevice], experiment_config: ExperimentConfig
) -> dict[DeviceName, "Camera"]:
    return {
        device_name: device  # type: ignore
        for device_name, device in devices.items()
        if isinstance(
            experiment_config.get_device_config(device_name),
            CameraConfiguration,
        )
    }


def get_tweezer_arrangers_in_use(
    devices: Mapping[DeviceName, RuntimeDevice], experiment_config: ExperimentConfig
) -> dict[DeviceName, "AODTweezerArranger"]:
    return {
        device_name: device  # type: ignore
        for device_name, device in devices.items()
        if isinstance(
            experiment_config.get_device_config(device_name),
            AODTweezerArrangerConfiguration,
        )
    }


def update_device(device: RuntimeDevice, parameters: Mapping[DeviceParameter, Any]):
    try:
        if parameters:
            with DurationTimerLog(
                logger, f"Updating device {device.get_name()}", display_start=True
            ):
                device.update_parameters(**parameters)
    except Exception as error:
        raise RuntimeError(f"Failed to update device {device.get_name()}") from error
