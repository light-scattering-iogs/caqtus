import collections
from collections.abc import Set

import anyio

from caqtus.device import DeviceName
from caqtus.types.data import DataLabel, Data
from .._logger import logger


class ShotEventDispatcher:
    def __init__(self, devices_in_use: Set[DeviceName]):
        self._devices_in_use = devices_in_use
        self._device_ready = {device: anyio.Event() for device in devices_in_use}
        self._acquisition_events: dict[DataLabel, anyio.Event] = (
            collections.defaultdict(anyio.Event)
        )
        self._acquired_data: dict[DataLabel, Data] = {}

    def _reset(self) -> None:
        self.__init__(self._devices_in_use)

    def signal_device_ready(self, device: DeviceName) -> None:
        if device not in self._device_ready:
            raise ValueError(f"Device {device} is not in use")
        if self._device_ready[device].is_set():
            raise ValueError(f"Device {device} is already ready")
        self._device_ready[device].set()
        logger.debug(f"Device {device} signaled ready")

    async def wait_device_ready(self, device: DeviceName) -> None:
        if device not in self._device_ready:
            raise ValueError(f"Device {device} is not in use")
        await self._device_ready[device].wait()

    async def wait_all_devices_ready(self, waiting_device: DeviceName) -> None:
        logger.debug(
            f"Device {waiting_device} started waiting for all devices to be ready"
        )
        async with anyio.create_task_group() as tg:
            for event in self._device_ready.values():
                tg.start_soon(event.wait)
        logger.debug(
            f"Device {waiting_device} finished waiting for all devices to be ready"
        )

    async def wait_data_acquired(
        self, waiting_device: DeviceName, label: DataLabel
    ) -> Data:
        logger.debug(
            f"Device {waiting_device} started waiting for data {label} to be acquired"
        )
        if label not in self._acquired_data:
            await self._acquisition_events[label].wait()
        logger.debug(
            f"Device {waiting_device} finished waiting for data {label} to be acquired"
        )
        return self._acquired_data[label]

    def signal_data_acquired(
        self, emitting_device: DeviceName, label: DataLabel, data: Data
    ) -> None:
        if label in self._acquired_data:
            raise KeyError(f"There is already data acquired for label {label}")
        else:
            self._acquired_data[label] = data
            if label in self._acquisition_events:
                self._acquisition_events[label].set()
            logger.debug(f"Device {emitting_device} acquired data {label}")

    def waiting_on_data(self) -> Set[DataLabel]:
        return set(
            label
            for label, event in self._acquisition_events.items()
            if not event.is_set()
        )

    def acquired_data(self) -> dict[DataLabel, Data]:
        if not_acquired := self.waiting_on_data():
            raise RuntimeError(
                f"Still waiting on data acquisition for labels {not_acquired}"
            )
        return self._acquired_data

    def _device_signaled_ready(self, device: DeviceName) -> bool:
        return self._device_ready[device].is_set()
