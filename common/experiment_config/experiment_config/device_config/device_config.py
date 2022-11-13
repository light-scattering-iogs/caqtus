from abc import abstractmethod, ABC
from typing import TypeVar

from pydantic import Field

from settings_model import SettingsModel


class DeviceConfiguration(SettingsModel, ABC):
    """Handle the static experiment wide configuration of a device"""

    device_name: str = Field(
        description="A unique identifier name given to the device."
    )
    remote_server: str = Field(
        description="The name of the server that will actually instantiate the device."
    )

    @abstractmethod
    def get_device_type(self) -> str:
        ...

    def get_device_init_args(self) -> dict[str]:
        return {"name": self.device_name}


DeviceConfigType = TypeVar("DeviceConfigType", bound=DeviceConfiguration)
