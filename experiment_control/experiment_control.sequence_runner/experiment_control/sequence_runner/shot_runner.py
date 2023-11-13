import asyncio
import collections
import contextlib
import datetime
import itertools
import logging
import threading
import time
from typing import Mapping, Iterable, Self, Any

from camera.runtime import Camera, CameraTimeoutError
from data_types import Data, DataLabel
from device.configuration import DeviceParameter
from device.name import DeviceName
from device.runtime import RuntimeDevice
from experiment_control.compute_device_parameters.image_analysis import (
    FromImageToDetector,
    FromDetectorToArranger,
)
from image_types import ImageLabel, Image
from sequencer.runtime import Sequencer
from tweezer_arranger.runtime import TweezerArranger, RearrangementFailedError
from util import DurationTimer, attrs, DurationTimerLog

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@attrs.frozen
class ShotResult:
    start_time: datetime.datetime
    end_time: datetime.datetime
    data: dict[DeviceName, dict[DataLabel, Data]]


class ShotRunner(contextlib.AbstractContextManager):
    """Runs shot on the experiment.

    All communication with the devices are done inside this class.
    """

    def __init__(
        self,
        sequencers: Mapping[DeviceName, Sequencer],
        cameras: Mapping[DeviceName, Camera],
        tweezer_arrangers: Mapping[DeviceName, TweezerArranger],
        extra_devices: Mapping[DeviceName, RuntimeDevice],
        analysis_flow: tuple[FromImageToDetector, FromDetectorToArranger],
    ):
        """Create a shot runner.

        When creating a shot runner, you must provide all the devices that will be used for running the shots. They must
        be separated into sequencers, cameras, tweezer arrangers, and other devices that don't fit into those
        categories. This is because when running a shot, sequencers, cameras, and tweezer arrangers must be handled
        with specific care, while other devices don't have a special treatment.

        All the devices must have unique names, even if they are of different types, i.e. each device must be
        identifiable by its name alone.

        The device must be uninitialized. The method `initialize` will be called on each device when the shot runner
        is entered. The method `close` will be called on each device when the shot runner is exited.
        """

        _check_name_unique(
            itertools.chain(sequencers, cameras, tweezer_arrangers, extra_devices)
        )
        self._sequencers = dict(sequencers)
        self._cameras = dict(cameras)
        self._tweezer_arrangers = dict(tweezer_arrangers)
        self._extra_devices = dict(extra_devices)
        self._devices = {
            **self._sequencers,
            **self._cameras,
            **self._tweezer_arrangers,
            **self._extra_devices,
        }

        self._image_flow, self._rearrange_flow = analysis_flow

        self._exit_stack = contextlib.ExitStack()
        self._lock = threading.Lock()

    def __enter__(self) -> Self:
        """Prepare to run shots.

        When entering the shot runner, all the devices will be initialized.
        Cannot be used inside an already running asyncio event loop.
        """

        self._exit_stack.__enter__()
        try:
            self._initialize_devices()
        except Exception:
            self._exit_stack.close()
            raise
        return self

    def _initialize_devices(self) -> None:
        asyncio.run(self._initialize_devices_async())

    async def _initialize_devices_async(self) -> None:
        async with asyncio.TaskGroup() as g:
            for device_name, device in self._devices.items():
                g.create_task(asyncio.to_thread(self._initialize_device, device))

    def _initialize_device(self, device: RuntimeDevice) -> None:
        # We don't initialize the device inside the lock because we want to initialize all the devices in parallel in
        # different threads. If we were to initialize the devices inside the lock, it would be sequential.
        device.initialize()
        with self._lock:
            # However, ExitStack is not thread-safe, so we protect it.
            self._exit_stack.enter_context(contextlib.closing(device))

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Performs cleanup after running shots.

        When exiting the shot runner, all the devices in use will be closed.
        """

        return self._exit_stack.__exit__(exc_type, exc_val, exc_tb)

    def do_shot(
        self,
        device_parameters: Mapping[DeviceName, Mapping[DeviceParameter, Any]],
        number_of_attempts: int,
    ) -> ShotResult:
        """Run a shot, retrying if it fails because of a camera timeout or a rearrangement failure.

        Cannot be used inside an already running asyncio event loop. If you need to do so, you will need to run this
        method in a new thread.
        """

        return asyncio.run(
            self._do_shot_with_retry(device_parameters, number_of_attempts)
        )

    async def _do_shot_with_retry(
        self,
        device_parameters: Mapping[DeviceName, Mapping[DeviceParameter, Any]],
        number_of_attempts: int,
    ) -> ShotResult:

        number_of_attempts = int(number_of_attempts)
        if number_of_attempts < 1:
            raise ValueError("number_of_attempts must be >= 1")

        for attempt in range(number_of_attempts):
            errors: list[Exception] = []
            try:
                with DurationTimer() as timer:
                    data = await self._do_single_shot(device_parameters)
            except* CameraTimeoutError as e:
                errors.extend(e.exceptions)
                logger.warning(
                    "A camera timeout error occurred, attempting to redo the failed shot"
                )
            except* RearrangementFailedError as e:
                errors.extend(e.exceptions)
                logger.warning("Rearrangement failed, attempting to redo the shot")
            else:
                return ShotResult(
                    start_time=timer.start_time,
                    end_time=timer.end_time,
                    data=data,
                )
            logger.warning(f"Attempt {attempt+1}/{number_of_attempts} failed")
        # noinspection PyUnboundLocalVariable
        raise ExceptionGroup(
            f"Could not execute shot after {number_of_attempts} attempts", errors
        )

    async def _do_single_shot(
        self,
        device_parameters: Mapping[DeviceName, Mapping[DeviceParameter, Any]],
    ) -> dict[DeviceName, dict[DataLabel, Data]]:
        with DurationTimerLog(logger, "Updating devices", display_start=True):
            await self._update_device_parameters(device_parameters)

        with DurationTimerLog(logger, "Performing shot", display_start=True):
            data = await self._perform_shot()
        return data

    async def _update_device_parameters(
        self, device_parameters: Mapping[DeviceName, Mapping[DeviceParameter, Any]]
    ):
        async with asyncio.TaskGroup() as g:
            for device_name, parameters in device_parameters.items():
                g.create_task(
                    asyncio.to_thread(
                        update_device, self._devices[device_name], parameters
                    )
                )

    async def _perform_shot(self) -> dict[DeviceName, dict[DataLabel, Data]]:
        data: dict[DeviceName, dict[DataLabel, Data]] = {}

        with DurationTimerLog(logger, "Launching shot", display_start=True):
            await self._launch_shot()

        with DurationTimerLog(logger, "Running shot", display_start=True):
            camera_tasks = {}
            async with asyncio.TaskGroup() as g:
                for camera_name, camera in self._cameras.items():
                    camera_tasks[camera_name] = g.create_task(
                        asyncio.to_thread(
                            self.fetch_and_analyze_images, camera_name, camera
                        )
                    )
                for sequencer in self._sequencers.values():
                    g.create_task(asyncio.to_thread(wait_on_sequencer, sequencer))

        for camera_name, camera_task in camera_tasks.items():
            data |= camera_task.result()

        self._finish_shot()

        return data

    async def _launch_shot(self):
        sequencers = list(self._sequencers.values())
        async with asyncio.TaskGroup() as g:
            for tweezer_arranger in self._tweezer_arrangers.values():
                # Interface for tweezer arrangers is not fully defined yet, so some methods call are specific to
                # AODTweezerArranger
                g.create_task(asyncio.to_thread(tweezer_arranger.start_sequence))
            for camera in self._cameras.values():
                g.create_task(asyncio.to_thread(camera.start_acquisition))
            for sequencer in sequencers[:-1]:
                g.create_task(asyncio.to_thread(sequencer.start_sequence))

        # We start the sequencer with the lower priority last so that it can trigger the other sequencers.
        sequencers[-1].start_sequence()

    def fetch_and_analyze_images(
        self, camera_name: DeviceName, camera: "Camera"
    ) -> dict[DeviceName, dict[DataLabel, Data]]:
        picture_names = camera.get_picture_names()

        result: dict[DeviceName, dict[DataLabel, Data]] = {}
        pictures = {}
        for picture_name in picture_names:
            picture = get_picture_from_camera(camera, picture_name)
            pictures[picture_name] = picture
            if (camera_name, picture_name) in self._image_flow:
                for detector, imaging_config in self._image_flow[
                    (camera_name, picture_name)
                ]:
                    atoms = self._devices[detector].are_atoms_present(
                        picture, imaging_config
                    )
                    if detector not in result:
                        result[detector] = {}
                    result[detector][picture_name] = atoms
                    if (detector, picture_name) in self._rearrange_flow:
                        tweezer_arranger, step = self._rearrange_flow[
                            (detector, picture_name)
                        ]
                        self._tweezer_arrangers[tweezer_arranger].prepare_rearrangement(
                            step=step, atom_present=atoms
                        )
        camera.stop_acquisition()
        logger.debug(f"Stopped acquisition of camera '{camera.get_name()}'")

        result[camera_name] = pictures
        return result

    def _finish_shot(self):
        for tweezer_arranger in self._tweezer_arrangers.values():
            tweezer_arranger.save_awg_data()


def _check_name_unique(names: Iterable[DeviceName]):
    counts = collections.Counter(names)
    for name, count in counts.items():
        if count > 1:
            raise ValueError(f"Device name {name} is used more than once")


def update_device(device: RuntimeDevice, parameters: Mapping[DeviceParameter, Any]):
    try:
        if parameters:
            with DurationTimerLog(
                logger, f"Updating device {device.get_name()}", display_start=True
            ):
                device.update_parameters(**parameters)
    except Exception as error:
        raise RuntimeError(f"Failed to update device {device.get_name()}") from error


def wait_on_sequencer(sequencer: Sequencer):
    """Wait for a sequencer to finish."""

    while not sequencer.has_sequence_finished():
        time.sleep(10e-3)


def get_picture_from_camera(camera: Camera, picture_name: ImageLabel) -> Image:
    while (image := camera.get_picture(picture_name)) is None:
        time.sleep(1e-3)
    return image
