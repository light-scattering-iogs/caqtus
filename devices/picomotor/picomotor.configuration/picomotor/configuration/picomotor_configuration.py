from typing import Optional

from pydantic import IPvAnyAddress, Field
from pydantic.color import Color

from device_config import DeviceConfiguration
from device_config.channel_config import (
    AnalogChannelConfiguration,
)


class PicomotorConfiguration(DeviceConfiguration, AnalogChannelConfiguration):
    number_channels = 4

    address: IPvAnyAddress = Field(
        description="The IP address of the picomotor controller."
    )

    channel_descriptions: list[str] = [f"actuator {i+1}" for i in range(number_channels)]
    channel_colors: list[Optional[Color]] = [None] * number_channels

    def get_device_type(self) -> str:
        return "PicomotorController"
