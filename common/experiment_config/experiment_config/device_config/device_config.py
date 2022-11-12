from pydantic import Field

from settings_model import SettingsModel


class DeviceConfiguration(SettingsModel):
    """Handle the static experiment wide configuration of a device"""

    device_name: str = Field(
        description="A unique identifier name given to the device."
    )
    device_type: str = Field(
        description="The class name of the device. It must be a subclass of CDevice."
    )
    remote_server: str = Field(
        description="The name of the server that will actually instantiate the device."
    )
    init_args: dict[str] = Field(
        default_factory=dict,
        description="Extra arguments that are passed as such when creating the device object.",
    )
