from __future__ import annotations

from typing import ClassVar, Type

import attrs

from caqtus.device import DeviceName
from caqtus.device.sequencer import SequencerConfiguration, AnalogChannelConfiguration
from caqtus.device.sequencer.configuration.configuration import SequencerUpdateParams
from caqtus.shot_compilation import SequenceContext, ShotContext
from caqtus.utils import serialization
from ..runtime import NI6738AnalogCard


@attrs.define
class NI6738SequencerConfiguration(SequencerConfiguration[NI6738AnalogCard]):
    @classmethod
    def channel_types(cls) -> tuple[Type[AnalogChannelConfiguration], ...]:
        return (AnalogChannelConfiguration,) * cls.number_channels

    number_channels: ClassVar[int] = 32
    device_id: str = attrs.field(converter=str, on_setattr=attrs.setters.convert)
    channels: tuple[AnalogChannelConfiguration, ...] = attrs.field(
        converter=tuple,
        validator=attrs.validators.deep_iterable(
            member_validator=attrs.validators.instance_of(AnalogChannelConfiguration)
        ),
        on_setattr=attrs.setters.pipe(attrs.setters.convert, attrs.setters.validate),
    )
    time_step: int = attrs.field(
        default=25000,
        converter=int,
        validator=attrs.validators.ge(2500),
        on_setattr=attrs.setters.pipe(attrs.setters.convert, attrs.setters.validate),
    )

    @channels.validator  # type: ignore
    def validate_channels(self, attribute, channels: list[AnalogChannelConfiguration]):
        super().validate_channels(attribute, channels)
        for channel in channels:
            if channel.output_unit != "V":
                raise ValueError(
                    f"Channel {channel} output units ({channel.output_unit}) are not"
                    " compatible with Volt"
                )

    def get_device_initialization_method(
        self, device_name: DeviceName, sequence_context: SequenceContext
    ):
        return (
            super()
            .get_device_initialization_method(device_name, sequence_context)
            .with_extra_parameters(name=device_name, device_id=self.device_id)
        )

    def compile_device_shot_parameters(
        self,
        device_name: DeviceName,
        shot_context: ShotContext,
    ) -> SequencerUpdateParams:
        return super().compile_device_shot_parameters(device_name, shot_context)

    @classmethod
    def dump(cls, obj: NI6738SequencerConfiguration) -> serialization.JSON:
        return serialization.converters["json"].unstructure(
            obj, NI6738SequencerConfiguration
        )

    @classmethod
    def load(cls, data: serialization.JSON) -> NI6738SequencerConfiguration:
        return serialization.converters["json"].structure(
            data, NI6738SequencerConfiguration
        )
