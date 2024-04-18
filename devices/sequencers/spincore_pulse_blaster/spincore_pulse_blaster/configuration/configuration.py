from __future__ import annotations

from typing import ClassVar, Type, TYPE_CHECKING

import attrs

from caqtus.device import DeviceName
from caqtus.device.sequencer import (
    SequencerConfiguration,
    ChannelConfiguration,
    DigitalChannelConfiguration,
    SoftwareTrigger,
)
from caqtus.device.sequencer.configuration import Constant
from caqtus.device.sequencer.configuration.configuration import SequencerUpdateParams
from caqtus.shot_compilation import SequenceContext, ShotContext
from caqtus.types.expression import Expression
from caqtus.utils import serialization

if TYPE_CHECKING:
    # noinspection PyUnresolvedReferences
    from ..runtime import SpincorePulseBlaster


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

    def get_device_initialization_method(
        self, device_name: DeviceName, sequence_context: SequenceContext
    ):
        return (
            super()
            .get_device_initialization_method(device_name, sequence_context)
            .with_extra_parameters(name=device_name, board_number=self.board_number)
        )

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

    @classmethod
    def default(cls) -> SpincoreSequencerConfiguration:
        return SpincoreSequencerConfiguration(
            remote_server=None,
            board_number=0,
            time_step=50,
            channels=tuple(
                [
                    DigitalChannelConfiguration(
                        description=f"Channel {channel}",
                        output=Constant(Expression("Disabled")),
                    )
                    for channel in range(SpincoreSequencerConfiguration.number_channels)
                ]
            ),
            trigger=SoftwareTrigger(),
        )
