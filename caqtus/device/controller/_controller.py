import abc

from caqtus.device import DeviceName
from caqtus.shot_event_dispatcher import ShotEventDispatcher


class DeviceController(abc.ABC):
    """Controls a device during a shot."""

    def __init__(
        self, device_name: DeviceName, shot_event_dispatcher: ShotEventDispatcher
    ):
        self._shot_event_dispatcher = shot_event_dispatcher
        self._device_name = device_name

    def signal_ready(self) -> None:
        """Indicates that the device has been programed and is ready to run the shot."""

        self._shot_event_dispatcher.signal_device_ready(self._device_name)

    @abc.abstractmethod
    async def run_shot(self) -> None:
        self.signal_ready()
