import abc
from typing import Generic, TypeVar

from caqtus.shot_event_dispatcher import ShotEventDispatcher
from ..runtime import Device

DeviceType = TypeVar("DeviceType", bound=Device)


class DeviceController(Generic[DeviceType], abc.ABC):
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

    @abc.abstractmethod
    async def run_shot(self) -> None:
        self.signal_ready()
