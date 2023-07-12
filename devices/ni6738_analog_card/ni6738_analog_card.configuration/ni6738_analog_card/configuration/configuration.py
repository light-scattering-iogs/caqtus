from typing import Any, ClassVar, Type

from pydantic import validator, Field

from device.configuration import DeviceParameter
from sequencer.configuration import (
    SequencerConfiguration,
    AnalogChannelConfiguration,
    ChannelConfiguration,
)


class NI6738SequencerConfiguration(SequencerConfiguration):
    @classmethod
    def channel_types(cls) -> tuple[Type[ChannelConfiguration], ...]:
        return (AnalogChannelConfiguration,) * cls.number_channels

    number_channels: ClassVar[int] = 32
    device_id: str
    time_step: float = Field(ge=2.5e-6)
    channels: tuple[AnalogChannelConfiguration, ...]

    @validator("channels")
    def validate_channels(cls, channels: list[AnalogChannelConfiguration]):
        channels = super().validate_channels(channels)
        for channel in channels:
            mapping = channel.output_mapping
            if (output_units := mapping.get_output_units()) != "V":
                raise ValueError(
                    f"Channel {channel} output units ({output_units}) are not"
                    " compatible with Volt"
                )
        return channels

    def get_device_type(self) -> str:
        return "NI6738AnalogCard"

    def get_device_init_args(self) -> dict[DeviceParameter, Any]:
        extra = {
            "device_id": self.device_id,
            "time_step": self.time_step,
            "external_clock": True,
        }
        return super().get_device_init_args() | extra
