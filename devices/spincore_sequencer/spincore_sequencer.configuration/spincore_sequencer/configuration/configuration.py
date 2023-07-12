from typing import Any, ClassVar, Type

from pydantic import Field

from device.configuration import DeviceParameter
from sequencer.configuration import (
    SequencerConfiguration,
    ChannelConfiguration,
    DigitalChannelConfiguration,
)


class SpincoreSequencerConfiguration(SequencerConfiguration):
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

    board_number: int
    time_step: float = Field(
        default=50e-9,
        ge=50e-9,
    )
    channels: tuple[DigitalChannelConfiguration, ...]

    def get_device_type(self) -> str:
        return "SpincorePulseBlaster"

    def get_device_init_args(self) -> dict[DeviceParameter, Any]:
        extra = {
            "board_number": self.board_number,
            "time_step": self.time_step,
        }
        return super().get_device_init_args() | extra
