from typing import ClassVar, Any

from device.configuration import DeviceParameter
from sequencer.configuration import (
    SequencerConfiguration,
    ChannelConfiguration,
    DigitalChannelConfiguration,
)


class SwabianPulseStreamerConfiguration(SequencerConfiguration):
    number_channels: ClassVar[int] = 8

    ip_address: str

    time_step: int

    @classmethod
    def channel_types(cls) -> tuple[type[ChannelConfiguration], ...]:
        return (DigitalChannelConfiguration,) * cls.number_channels

    def get_device_type(self) -> str:
        return "SwabianPulseStreamer"

    def get_device_init_args(self, *args, **kwargs) -> dict[DeviceParameter, Any]:
        extra = {
            "ip_address": self.ip_address,
            "time_step": self.time_step,
        }
        return super().get_device_init_args(*args, **kwargs) | extra
