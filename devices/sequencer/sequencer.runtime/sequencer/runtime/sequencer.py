from abc import ABC
from typing import ClassVar

from pydantic import Field

from device.runtime import RuntimeDevice
from sequencer.instructions import SequencerInstruction


class Sequencer(RuntimeDevice, ABC):
    """Base class for all sequencers.

    Fields:
        time_step: The time step of the sequencer in nanoseconds.
    """

    channel_number: ClassVar[int]
    time_step: int = Field(ge=1, allow_mutation=False)

    def update_parameters(self, *_, sequence: SequencerInstruction, **kwargs) -> None:
        raise NotImplementedError
