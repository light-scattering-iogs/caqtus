from typing import ClassVar, Any, Type, Self

from device.configuration import DeviceParameter
from sequencer.configuration import (
    SequencerConfiguration,
    ChannelConfiguration,
    DigitalChannelConfiguration,
    DigitalMapping,
    ChannelName,
)


class SwabianPulseStreamerConfiguration(SequencerConfiguration):
    number_channels: ClassVar[int] = 8

    ip_address: str

    time_step: int

    @classmethod
    def channel_types(cls) -> tuple[Type[ChannelConfiguration], ...]:
        return (DigitalChannelConfiguration,) * cls.number_channels

    def get_device_type(self) -> str:
        return "SwabianPulseStreamer"

    def get_device_init_args(self, *args, **kwargs) -> dict[DeviceParameter, Any]:
        extra = {
            "ip_address": self.ip_address,
            "time_step": self.time_step,
        }
        return super().get_device_init_args(*args, **kwargs) | extra

    @classmethod
    def get_default_config(cls, device_name: str, remote_server: str) -> Self:
        return cls(
            device_name=device_name,
            remote_server=remote_server,
            ip_address="",
            time_step=1,
            channels=tuple(
                DigitalChannelConfiguration(
                    output_mapping=DigitalMapping(), description=ChannelName("")
                )
                for _ in range(cls.number_channels)
            ),
        )
