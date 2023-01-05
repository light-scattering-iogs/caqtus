from pydantic import Field

from device_config import DeviceConfiguration
from device_config.channel_config import DigitalChannelConfiguration


class SpincoreSequencerConfiguration(DeviceConfiguration, DigitalChannelConfiguration):
    # noinspection PyPropertyDefinition
    @classmethod
    @property
    def number_channels(cls) -> int:
        return 24

    board_number: int
    time_step: float = Field(
        default=50e-9,
        ge=50e-9,
        units="s",
        description=(
            "The quantization time step used when converting step times to"
            " instructions."
        ),
    )

    def get_device_type(self) -> str:
        return "SpincorePulseBlaster"

    def get_device_init_args(self) -> dict[str]:
        extra = {
            "board_number": self.board_number,
            "time_step": self.time_step,
        }
        return super().get_device_init_args() | extra
