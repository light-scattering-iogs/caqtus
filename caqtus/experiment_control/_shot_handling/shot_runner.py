import contextlib
from collections.abc import Mapping
from typing import Any

import anyio
import anyio.to_thread

from caqtus.device import DeviceName, Device
from caqtus.device.controller import DeviceController
from caqtus.types.data import DataLabel, Data
from . import ShotEventDispatcher
from ._shot_event_dispatcher import DeviceRunConfig


class ShotRunner:
    def __init__(
        self,
        devices: Mapping[DeviceName, Device],
        controller_types: Mapping[DeviceName, type[DeviceController]],
    ):
        if set(devices.keys()) != set(controller_types.keys()):
            raise ValueError("The devices and controller_types must have the same keys")
        self.devices = devices
        self.controller_types = controller_types
        self.exit_stack = contextlib.ExitStack()

    def __enter__(self):
        self.exit_stack.__enter__()
        try:
            anyio.run(self._enter_async, backend="trio")
        except Exception as e:
            # If an error occurs while initializing a device, we close the exit stack to
            # ensure that all devices are exited.
            self.exit_stack.__exit__(type(e), e, e.__traceback__)
            raise
        return self

    async def _enter_async(self):
        async with anyio.create_task_group() as tg:
            for device in self.devices.values():
                tg.start_soon(self._enter_device, device)

    async def _enter_device(self, device: Device) -> None:
        with anyio.CancelScope(shield=True):
            await anyio.to_thread.run_sync(device.__enter__)
            self.exit_stack.push(device)

    def run_shot(
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
        return anyio.run(
            event_dispatcher.run_shot,
            timeout,
            backend="trio",
        )

    def __exit__(self, exc_type, exc_value, traceback):
        self.exit_stack.__exit__(exc_type, exc_value, traceback)
