from abc import ABC, abstractmethod
from typing import ClassVar

from attr import define, field
from attr.setters import frozen
from attr.validators import ge, instance_of

from device.runtime import RuntimeDevice
from sequencer.configuration.trigger import Trigger, SoftwareTrigger
from sequencer.instructions.struct_array_instruction import SequencerInstruction


@define(slots=False)
class Sequencer(RuntimeDevice, ABC):
    """Base class for all sequencers.

    Fields:
        time_step: The time step of the sequencer in nanoseconds.
        trigger: Indicates how the sequence is started and how it is clocked.
    """

    channel_number: ClassVar[int]

    time_step: int = field(on_setattr=frozen, converter=int, validator=ge(1))
    trigger: Trigger = field(
        factory=SoftwareTrigger, on_setattr=frozen, validator=instance_of(Trigger)
    )

    _sequence_programmed: bool = field(default=False, init=False)
    _sequence_started: bool = field(default=False, init=False)

    @abstractmethod
    def update_parameters(self, *_, sequence: SequencerInstruction, **kwargs) -> None:
        """Update the parameters of the sequencer.

        To be subclassed by the specific sequencer implementation. The base class implementation set
        _sequence_programmed to True.

        Args:
            sequence: The sequence to be programmed into the sequencer.
        """

        if sequence.width != self.channel_number:
            raise ValueError(
                f"Invalid number of channels. Expected {self.channel_number}, got"
                f" {sequence.width}."
            )

    def _set_sequence_programmed(self) -> None:
        """To call after successful update_parameters."""

        self._sequence_started = False
        self._sequence_programmed = True

    @abstractmethod
    def start_sequence(self) -> None:
        """Start the sequence.

        To be subclassed by the specific sequencer implementation. The base class implementation checks if the sequence
        has been programmed and sets _sequence_started to True.
        Raises:
            SequenceNotConfiguredError: If the sequence has not been configured yet.
        """

        if not self._sequence_programmed:
            raise SequenceNotConfiguredError("The sequence has not been set yet.")

        self._sequence_started = True
        self._sequence_programmed = False

    @abstractmethod
    def has_sequence_finished(self) -> bool:
        """Check if the sequence has finished.

        Returns:
            True if the sequence has finished, False if it is still running.
        Raises:
            SequenceNotStartedError: If start_sequence has not been called yet.
        """

        if not self._sequence_started:
            raise SequenceNotStartedError("The sequence has not been started yet.")
        return True

    def wait_sequence_finished(self) -> None:
        while not self.has_sequence_finished():
            pass

    def get_trigger_priority(self) -> int:
        """Get the priority of the trigger.

        Returns:
            The priority of the trigger.
        """

        return self.trigger.priority

    @classmethod
    def exposed_remote_methods(cls) -> tuple[str, ...]:
        return super().exposed_remote_methods() + (
            "start_sequence",
            "has_sequence_finished",
            "wait_sequence_finished",
            "get_trigger_priority",
        )

    def close(self) -> None:
        try:
            self.wait_sequence_finished()
        except SequenceNotStartedError:
            pass
        finally:
            super().close()


class SequenceNotStartedError(RuntimeError):
    """Raised when the sequencer is asked to do something that requires it to have been started, but it has not been
    started yet.
    """

    pass


class SequenceNotConfiguredError(RuntimeError):
    """Raised when the sequencer is asked to do something that requires it to have been configured, but it has not been
    configured yet.
    """

    pass
