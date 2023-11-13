import asyncio
import collections
import concurrent.futures
import contextlib
import datetime
import itertools
import logging
import threading
from typing import Mapping, Iterable, Self, Any

from camera.runtime import Camera, CameraTimeoutError
from data_types import Data
from device.configuration import DeviceParameter
from device.name import DeviceName
from device.runtime import RuntimeDevice
from sequencer.runtime import Sequencer
from tweezer_arranger.runtime import TweezerArranger, RearrangementFailedError
from util import DurationTimer, attrs

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@attrs.frozen
class ShotResult:
    start_time: datetime.datetime
    end_time: datetime.datetime
    data: Data


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

        self._exit_stack = contextlib.ExitStack()
        self._thread_pool = concurrent.futures.ThreadPoolExecutor()
        self._lock = threading.Lock()

    def __enter__(self) -> Self:
        """Prepare to run shots.

        When entering the shot runner, all the devices will be initialized.
        Cannot be used inside an already running asyncio event loop.
        """

        self._exit_stack.__enter__()
        self._exit_stack.enter_context(self._thread_pool)
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

        Cannot be used inside an already running asyncio event loop.
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
                    data = await asyncio.to_thread(
                        self._do_single_shot,
                        device_parameters,
                    )
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


def _check_name_unique(names: Iterable[DeviceName]):
    counts = collections.Counter(names)
    for name, count in counts.items():
        if count > 1:
            raise ValueError(f"Device name {name} is used more than once")
