from collections.abc import Mapping
from typing import Any

from caqtus.device import DeviceName, DeviceController
from caqtus.types.data import DataLabel, Data
from . import ShotEventDispatcher
from ._shot_event_dispatcher import DeviceRunConfig
from ...device.remote import DeviceProxy


class ShotRunner:
    def __init__(
        self,
        devices: Mapping[DeviceName, DeviceProxy],
        controller_types: Mapping[DeviceName, type[DeviceController]],
    ):
        if set(devices.keys()) != set(controller_types.keys()):
            raise ValueError("The devices and controller_types must have the same keys")
        self.devices = devices
        self.controller_types = controller_types

    async def run_shot(
        self,
        device_parameters: Mapping[DeviceName, Mapping[str, Any]],
        timeout: float,
    ) -> Mapping[DataLabel, Data]:
        event_dispatcher = ShotEventDispatcher(
            {
                name: DeviceRunConfig(
                    device=self.devices[name],
                    controller_type=self.controller_types[name],
                    parameters=device_parameters[name],
                )
                for name in self.devices
            }
        )
        return await event_dispatcher.run_shot(timeout)
