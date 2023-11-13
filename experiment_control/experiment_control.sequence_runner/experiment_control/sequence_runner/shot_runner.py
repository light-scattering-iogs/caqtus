import asyncio
import collections
import concurrent.futures
import contextlib
import itertools
import threading
from typing import Mapping, Iterable, Self

from camera.runtime import Camera
from device.name import DeviceName
from device.runtime import RuntimeDevice
from sequencer.runtime import Sequencer
from tweezer_arranger.runtime import TweezerArranger


class ShotRunner(contextlib.AbstractContextManager):
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
        # We create a new loop in a new thread, because we don't know if we are running inside a loop already.
        self._thread_pool.submit(asyncio.run, self._initialize_devices()).result()

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


def _check_name_unique(names: Iterable[DeviceName]):
    counts = collections.Counter(names)
    for name, count in counts.items():
        if count > 1:
            raise ValueError(f"Device name {name} is used more than once")
