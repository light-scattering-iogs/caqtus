from typing import ClassVar, Any, Self

import attrs

from core.device import DeviceParameter
from core.device.sequencer import (
    SequencerConfiguration,
    DigitalChannelConfiguration,
)
from util import serialization


@attrs.define
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
    def channel_types(cls) -> tuple[type[DigitalChannelConfiguration], ...]:
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
    def dump(cls, config: Self) -> serialization.JSON:
        return serialization.converters["json"].unstructure(config, cls)

    @classmethod
    def load(cls, data: serialization.JSON) -> Self:
        return serialization.converters["json"].structure(data, cls)
