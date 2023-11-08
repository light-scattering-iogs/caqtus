from typing import ClassVar, Any, Type, Self

from device.configuration import DeviceParameter
from sequencer.configuration import (
    SequencerConfiguration,
    ChannelConfiguration,
    DigitalChannelConfiguration,
    DigitalMapping,
    ChannelName,
)
from settings_model import YAMLSerializable
from util import attrs


@attrs.define(slots=False)
class SwabianPulseStreamerConfiguration(SequencerConfiguration):
    number_channels: ClassVar[int] = 8

    ip_address: str = attrs.field(converter=str, on_setattr=attrs.setters.convert)

    channels: tuple[DigitalChannelConfiguration, ...] = attrs.field(
        converter=tuple,
        validator=attrs.validators.deep_iterable(
            member_validator=attrs.validators.instance_of(DigitalChannelConfiguration)
        ),
        on_setattr=attrs.setters.pipe(attrs.setters.convert, attrs.setters.validate),
    )

    @classmethod
    def channel_types(cls) -> tuple[Type[ChannelConfiguration], ...]:
        return (DigitalChannelConfiguration,) * cls.number_channels

    def get_device_type(self) -> str:
        return "SwabianPulseStreamer"

    def get_device_init_args(self, *args, **kwargs) -> dict[DeviceParameter, Any]:
        extra = {
            DeviceParameter("ip_address"): self.ip_address,
            DeviceParameter("time_step"): self.time_step,
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


YAMLSerializable.register_attrs_class(SwabianPulseStreamerConfiguration)
