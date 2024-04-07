from collections.abc import Mapping
from typing import ClassVar, Any, Self

import attrs

from caqtus.device import DeviceName
from caqtus.device.sequencer import (
    SequencerConfiguration,
    DigitalChannelConfiguration,
)
from caqtus.device.sequencer.configuration.configuration import SequencerUpdateParams
from caqtus.shot_compilation import SequenceContext, ShotContext
from caqtus.utils import serialization
from ..runtime import SwabianPulseStreamer


@attrs.define
class SwabianPulseStreamerConfiguration(SequencerConfiguration[SwabianPulseStreamer]):
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

    def get_device_initialization_method(
        self, device_name: DeviceName, sequence_context: SequenceContext
    ) -> Mapping[str, Any]:
        return (
            super()
            .get_device_initialization_method(device_name, sequence_context)
            .with_extra_parameters(
                name=device_name,
                ip_address=self.ip_address,
            )
        )

    def compile_device_shot_parameters(
        self,
        device_name: DeviceName,
        shot_context: ShotContext,
    ) -> SequencerUpdateParams:
        return super().compile_device_shot_parameters(device_name, shot_context)

    @classmethod
    def dump(cls, config: Self) -> serialization.JSON:
        return serialization.converters["json"].unstructure(config, cls)

    @classmethod
    def load(cls, data: serialization.JSON) -> Self:
        return serialization.converters["json"].structure(data, cls)
