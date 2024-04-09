import contextlib
import functools
from collections.abc import Mapping
from typing import Any

import anyio
import anyio.to_thread

from caqtus.device import DeviceName, Device
from caqtus.device.controller import DeviceController
from caqtus.types.data import DataLabel, Data
from ._shot_event_dispatcher import ShotEventDispatcher
from .._logger import logger


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

        self.event_dispatcher = ShotEventDispatcher(set(self.devices.keys()))

        self.controllers = {
            name: controller_type(name, self.event_dispatcher)
            for name, controller_type in self.controller_types.items()
        }

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
        # noinspection PyProtectedMember
        self.event_dispatcher._reset()
        return anyio.run(
            functools.partial(self._run_shot_async, device_parameters, timeout),
            backend="trio",
        )

    async def _run_shot_async(
        self, device_parameters: Mapping[DeviceName, Mapping[str, Any]], timeout: float
    ) -> Mapping[DataLabel, Data]:
        logger.info(f"Shot started")
        with anyio.fail_after(timeout):
            async with anyio.create_task_group() as tg:
                for name, controller in self.controllers.items():
                    device = self.devices[name]
                    parameters = device_parameters[name]
                    tg.start_soon(
                        functools.partial(
                            self._wrap_run_shot, controller, device, **parameters
                        )
                    )

        logger.info("Shot finished")

        return self.event_dispatcher.acquired_data()

    async def _wrap_run_shot(self, controller: DeviceController, device, **parameters):
        await controller.run_shot(device, **parameters)
        device_name = controller.device_name
        if not self.event_dispatcher._device_signaled_ready(device_name):
            raise RuntimeError(
                f"The controller supervising the device '{device_name}' did not "
                f"call {controller.wait_all_devices_ready}."
            )

    def __exit__(self, exc_type, exc_value, traceback):
        self.exit_stack.__exit__(exc_type, exc_value, traceback)
