from __future__ import annotations

import collections
import time
from collections.abc import Set, Mapping
from typing import Any, Optional

import anyio
import attrs

from caqtus.device import DeviceName, DeviceController
from caqtus.device.remote import DeviceProxy
from caqtus.types.data import DataLabel, Data
from .shot_timing import ShotTimer
from .._logger import logger


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

        self._shot_timer: Optional[ShotTimer] = None

    async def run_shot(self, shot_timeout: float) -> Mapping[DataLabel, Data]:
        try:
            return await self._run_shot(shot_timeout)
        except:
            stats = {
                name: controller._debug_stats()
                for name, controller in self._controllers.items()
            }
            logger.debug("Shot trace: %s", stats)
            raise

    async def _run_shot(self, shot_timeout: float) -> Mapping[DataLabel, Data]:
        self._start_time = time.monotonic()
        result = {}
        # We shield running a shot from external cancellation, so that external
        # errors don't affect the shot.
        with anyio.CancelScope(shield=True):
            async with anyio.create_task_group() as tg:
                for name, info in self._device_infos.items():
                    # noinspection PyProtectedMember
                    tg.start_soon(
                        _save_in_dict,
                        info.controller._run_shot(
                            info.device, shot_timeout, info.parameters
                        ),
                        name,
                        result,
                    )

        data = self.acquired_data()
        data[DataLabel("shot analytics")] = result
        return data

    def shot_time(self) -> float:
        return time.monotonic() - self._start_time

    async def wait_all_devices_ready(self) -> ShotTimer:
        async with anyio.create_task_group() as tg:
            for controller in self._controllers.values():
                if not controller._signaled_ready.is_set():
                    # noinspection PyProtectedMember
                    tg.start_soon(controller._signaled_ready.wait)

        if self._shot_timer is None:
            # noinspection PyProtectedMember
            self._shot_timer = ShotTimer._create()
        return self._shot_timer

    async def wait_data_acquired(
        self, waiting_device: DeviceName, label: DataLabel
    ) -> Data:
        if label not in self._acquired_data:
            await self._acquisition_events[label].wait()
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
