from typing import ClassVar

from pydantic import Field

from device_config import DeviceConfiguration
from settings_model import SettingsModel


class SpectrumAWGM4i66xxX8Configuration(DeviceConfiguration):
    NUMBER_CHANNELS: ClassVar[int] = 2

    board_id: str = Field(
        description="An identifier to find the board. ex: /dev/spcm0",
    )
    sampling_rate: int = Field(units="Hz")
    channel_settings: tuple["ChannelSettings", ...] = Field(
        description="The configuration of the output channels", allow_mutation=False
    )

    def get_device_type(self) -> str:
        return "SpectrumAWGM4i66xxX8"

    def get_device_init_args(self) -> dict[str]:
        kwargs = {
            "board_id": self.board_id,
            "sampling_rate": self.sampling_rate,
            "channel_settings": self.channel_settings,
        }
        return super().get_device_init_args() | kwargs


class ChannelSettings(SettingsModel):
    name: str = Field(description="The name of the channel", allow_mutation=False)
    enabled: bool = Field(allow_mutation=False)
    amplitude: float = Field(
        description="The voltage amplitude of the output when setting the extrema values. ex: at an amplitude of 1 V, "
        "the output can swing between +1 V and -1 V in a 50 Ohm termination.",
        units="V",
        allow_mutation=False,
        ge=80e-3,
        le=2.5,
    )
    maximum_power: float = Field(
        description="Maximum average power per segment.",
        units="dBm",
        allow_mutation=False,
    )
