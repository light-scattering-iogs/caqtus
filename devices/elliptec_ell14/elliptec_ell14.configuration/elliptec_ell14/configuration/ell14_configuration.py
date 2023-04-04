from typing import Any

from device_config import DeviceConfiguration
from expression import Expression


class ElliptecELL14RotationStageConfiguration(DeviceConfiguration):
    """Holds static configuration to control an ELL14 rotation stage device

    Attributes:
        serial_port: The serial port to use to communicate with the device. e.g. "COM9"
        device_id: The device ID of the device. This is what is referred as the address in the thorlabs Ello software.
            If the device is used in multi-port mode, a single serial port can control multiple devices with different
            device IDs. However, this is not supported at the moment and only one device can be instantiated for a given
            serial port.
        position: The position of the stage in degrees. This can be an expression that depends on other variables.
            When these variables change, the new position will be recalculated in consequence and the stage will move to
            the new position.
    """

    serial_port: str
    device_id: int
    position: Expression

    def get_device_type(self) -> str:
        return "ElliptecELL14RotationStage"

    def get_device_init_args(self) -> dict[str, Any]:
        extra = {
            "serial_port": self.serial_port,
            "device_id": self.device_id,
        }
        return super().get_device_init_args() | extra
