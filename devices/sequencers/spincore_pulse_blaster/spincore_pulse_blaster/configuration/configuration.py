from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar, Type, TYPE_CHECKING

import attrs

from caqtus.device import DeviceName
from caqtus.device.sequencer import (
    SequencerConfiguration,
    ChannelConfiguration,
    DigitalChannelConfiguration,
)
from caqtus.device.sequencer.configuration.configuration import SequencerUpdateParams
from caqtus.shot_compilation import SequenceContext, ShotContext
from caqtus.utils import serialization

if TYPE_CHECKING:
    pass


@attrs.define
class SpincoreSequencerConfiguration(SequencerConfiguration["SpincorePulseBlaster"]):
    """Holds the static configuration of a spincore sequencer device.

    Fields:
        board_number: The number of the board to use. With only one board connected,
            this number is usually 0.
        time_step: The quantization time step used. All times during a run are multiples
            of this value.
    """

    @classmethod
    def channel_types(cls) -> tuple[Type[ChannelConfiguration], ...]:
        return (DigitalChannelConfiguration,) * cls.number_channels

    number_channels: ClassVar[int] = 24

    board_number: int = attrs.field(
        converter=int,
        on_setattr=attrs.setters.convert,
    )
    channels: tuple[DigitalChannelConfiguration, ...] = attrs.field(
        converter=tuple,
        validator=attrs.validators.deep_iterable(
            member_validator=attrs.validators.instance_of(DigitalChannelConfiguration)
        ),
        on_setattr=attrs.setters.pipe(attrs.setters.convert, attrs.setters.validate),
    )
    time_step: int = attrs.field(
        default=50,
        converter=int,
        validator=attrs.validators.ge(50),
        on_setattr=attrs.setters.pipe(attrs.setters.convert, attrs.setters.validate),
    )

    def get_device_init_args(
        self, device_name: DeviceName, sequence_context: SequenceContext
    ) -> Mapping[str, Any]:
        return super().get_device_init_args(device_name, sequence_context) | {
            "board_number": self.board_number,
        }

    def compile_device_shot_parameters(
        self,
        device_name: DeviceName,
        shot_context: ShotContext,
    ) -> SequencerUpdateParams:
        return super().compile_device_shot_parameters(device_name, shot_context)

    @classmethod
    def dump(cls, configuration: SpincoreSequencerConfiguration) -> serialization.JSON:
        return serialization.unstructure(configuration, SpincoreSequencerConfiguration)

    @classmethod
    def load(cls, data) -> SpincoreSequencerConfiguration:
        return serialization.structure(data, SpincoreSequencerConfiguration)
