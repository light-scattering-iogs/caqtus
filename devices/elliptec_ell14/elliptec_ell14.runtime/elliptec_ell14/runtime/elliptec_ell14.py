"""This package defines a RuntimeDevice class that is used to control Thorlabs Elliptec ELL14 rotation stages."""
import time
from contextlib import closing
from typing import Optional

from serial import SerialException
from thorlabs_elliptec import ELLx, ELLStatus

from device import RuntimeDevice, Field


class ElliptecELL14RotationStage(RuntimeDevice):
    """A class for controlling Thorlabs Elliptec ELL14 rotation stages.

    Attributes:
        serial_port: The serial port to use to communicate with the device. e.g. "COM9"
        device_id: The device ID of the device. This is what is referred as the address in the thorlabs Ello software.
            If the device is used in multi-port mode, a single serial port can control multiple devices with different
            device IDs. However, this is not supported at the moment and only one device can be instantiated for a given
            serial port.
    """

    serial_port: str = Field(allow_mutation=False)
    device_id: int = Field(allow_mutation=False)
    initial_position: Optional[float] = Field(default=None, allow_mutation=False)

    _device: Optional[ELLx] = None

    class Config(RuntimeDevice.Config):
        validate_all = False

    def initialize(self) -> None:
        """Connect to the device and initialize it."""

        super().initialize()

        try:
            self._device = self._enter_context(
                closing(
                    ELLx(serial_port=self.serial_port, x=14, device_id=self.device_id)
                )
            )
        except SerialException:
            raise SerialException(
                f"Could not open serial port {self.serial_port} for device '{self.name}'"
            )
        while self._device.status != ELLStatus.OK:
            time.sleep(0.1)

        if self.initial_position is not None:
            self._update_position(self.initial_position)

    def update_parameters(self, position: float) -> None:
        """Move the stage to the given position.

        Args:
            position: The position to move the stage to in degrees.
        """

        self._update_position(position)

    def _update_position(self, position: float):
        try:
            self._device.move_absolute(position, blocking=True)
        except Exception as error:
            raise RuntimeError(
                f"Could not move device {self.name} to position {position}"
            ) from error

    @property
    def position(self) -> float:
        """The current position of the stage in degrees."""

        if self._device is None:
            raise RuntimeError(f"Device {self.name} was not started")
        return self._device.get_position()
