import abc
from typing import Generic, TypeVar

from caqtus.shot_event_dispatcher import ShotEventDispatcher
from ..runtime import Device

DeviceType = TypeVar("DeviceType", bound=Device)

ShotParametersType = TypeVar("ShotParametersType")


class DeviceController(Generic[DeviceType, ShotParametersType], abc.ABC):
    """Controls a device during a shot."""

    def __init__(
        self,
        device: DeviceType,
        shot_event_dispatcher: ShotEventDispatcher,
    ):
        self.device = device
        self.device_name = device.get_name()
        self.event_dispatcher = shot_event_dispatcher

    def signal_ready(self) -> None:
        """Indicates that the device has been programed and is ready to run the shot."""

        self.event_dispatcher.signal_device_ready(self.device_name)

    async def wait_all_devices_ready(self) -> None:
        """Waits for all devices to be ready to run the shot."""

        await self.event_dispatcher.wait_all_devices_ready()

    @abc.abstractmethod
    async def run_shot(self, shot_parameters: ShotParametersType) -> None:
        self.signal_ready()
