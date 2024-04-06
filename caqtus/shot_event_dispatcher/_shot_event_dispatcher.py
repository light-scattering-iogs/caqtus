from collections.abc import Set

import anyio

from caqtus.device import DeviceName


class ShotEventDispatcher:
    def __init__(self, devices_in_use: Set[DeviceName]):
        self._device_ready = {device: anyio.Event() for device in devices_in_use}

    def signal_device_ready(self, device: DeviceName) -> None:
        if device not in self._device_ready:
            raise ValueError(f"Device {device} is not in use")
        if self._device_ready[device].is_set():
            raise ValueError(f"Device {device} is already ready")
        self._device_ready[device].set()

    async def wait_device_ready(self, device: DeviceName) -> None:
        if device not in self._device_ready:
            raise ValueError(f"Device {device} is not in use")
        await self._device_ready[device].wait()

    async def wait_all_devices_ready(self) -> None:
        async with anyio.create_task_group() as tg:
            for event in self._device_ready.values():
                tg.start_soon(event.wait)
