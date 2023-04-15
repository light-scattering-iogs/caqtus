from abc import abstractmethod, ABC
from typing import TypeVar, Any

from settings_model import SettingsModel


class DeviceConfiguration(SettingsModel, ABC):
    """Handle the static experiment wide configuration of a device.

    Attributes:
        device_name: A unique identifier name given to the device.
        remote_server: The name of the server that will actually instantiate the device.
    """

    device_name: str
    remote_server: str

    @abstractmethod
    def get_device_type(self) -> str:
        ...

    def get_device_init_args(self) -> dict[str, Any]:
        return {"name": self.device_name}


DeviceConfigType = TypeVar("DeviceConfigType", bound=DeviceConfiguration)
