from abc import ABC, abstractmethod
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

    @abstractmethod
    def update_parameters(self, *_, sequence: SequencerInstruction, **kwargs) -> None:
        raise NotImplementedError

    @abstractmethod
    def start_sequence(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_sequence_finished(self) -> bool:
        raise NotImplementedError

    def wait_sequence_finished(self) -> None:
        while not self.is_sequence_finished():
            pass

