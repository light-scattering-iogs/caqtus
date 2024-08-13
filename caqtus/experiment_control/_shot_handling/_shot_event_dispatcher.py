import collections
import time
from collections.abc import Set, Mapping
from typing import Any

import anyio
import attrs

from caqtus.device import DeviceName, DeviceController
from caqtus.types.data import DataLabel, Data
from .._logger import logger
from ...device.remote import DeviceProxy


@attrs.define
class DeviceRunConfig:
    device: DeviceProxy
    controller_type: type[DeviceController]
    parameters: Mapping[str, Any]


@attrs.define
class DeviceRunInfo:
    controller: DeviceController
    device: DeviceProxy
    parameters: Mapping[str, Any]


class ShotEventDispatcher:
    def __init__(self, device_run_configs: Mapping[DeviceName, DeviceRunConfig]):
        logger.info(
            f"Creating ShotEventDispatcher with devices {device_run_configs.keys()}"
        )
        self._device_infos: dict[DeviceName, DeviceRunInfo] = {
            name: DeviceRunInfo(
                controller=config.controller_type(name, self),
                device=config.device,
                parameters=config.parameters,
            )
            for name, config in device_run_configs.items()
        }

        self._controllers: dict[DeviceName, DeviceController] = {
            name: info.controller for name, info in self._device_infos.items()
        }

        self._acquisition_events: dict[DataLabel, anyio.Event] = (
            collections.defaultdict(anyio.Event)
        )
        self._acquired_data: dict[DataLabel, Data] = {}
        self._start_time = 0.0

    async def run_shot(self, timeout: float) -> Mapping[DataLabel, Data]:
        try:
            return await self._run_shot(timeout)
        except:
            stats = {
                name: controller._debug_stats()
                for name, controller in self._controllers.items()
            }
            logger.debug("Shot trace: %s", stats)
            raise

    async def _run_shot(self, timeout: float) -> Mapping[DataLabel, Data]:
        self._start_time = time.monotonic()
        result = {}
        with anyio.fail_after(timeout):
            async with anyio.create_task_group() as tg:
                for name, info in self._device_infos.items():
                    # noinspection PyProtectedMember
                    tg.start_soon(
                        _save_in_dict,
                        info.controller._run_shot(info.device, **info.parameters),
                        name,
                        result,
                    )

        data = self.acquired_data()
        data[DataLabel("shot analytics")] = result
        return data

    def shot_time(self) -> float:
        return time.monotonic() - self._start_time

    async def wait_all_devices_ready(self) -> None:
        async with anyio.create_task_group() as tg:
            for controller in self._controllers.values():
                # noinspection PyProtectedMember
                tg.start_soon(controller._signaled_ready.wait)

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


async def _save_in_dict(task, key, dictionary):
    dictionary[key] = await task
