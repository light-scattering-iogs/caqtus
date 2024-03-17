from abc import ABC, abstractmethod
from typing import ClassVar

import attrs
from core.device import Device

from ..configuration import Trigger
from ..instructions import SequencerInstruction


@attrs.define(slots=False)
class Sequencer(Device, ABC):
    """Base class for all sequencers.

    Fields:
        time_step: The time step of the sequencer in nanoseconds.
        trigger: Indicates how the sequence is started and how it is clocked.
    """

    channel_number: ClassVar[int]

    time_step: int = attrs.field(
        on_setattr=attrs.setters.frozen, converter=int, validator=attrs.validators.ge(1)
    )
    trigger: Trigger = attrs.field(
        on_setattr=attrs.setters.frozen,
        validator=attrs.validators.instance_of(Trigger),
    )

    _sequence_programmed: bool = attrs.field(default=False, init=False)
    _sequence_started: bool = attrs.field(default=False, init=False)

    @abstractmethod
    def update_parameters(self, *_, sequence: SequencerInstruction, **kwargs) -> None:
        """Update the parameters of the sequencer.

        To be subclassed by the specific sequencer implementation.
        The base class implementation sets _sequence_programmed to True.

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

        To be subclassed by the specific sequencer implementation.
        The base class implementation checks if the sequence has been programmed and
        sets _sequence_started to True.

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

    def get_trigger(self) -> Trigger:
        return self.trigger

    @classmethod
    def exposed_remote_methods(cls) -> tuple[str, ...]:
        return super().exposed_remote_methods() + (
            "start_sequence",
            "has_sequence_finished",
            "wait_sequence_finished",
            "get_trigger",
        )

    def close(self) -> None:
        try:
            self.wait_sequence_finished()
        except SequenceNotStartedError:
            pass
        finally:
            super().close()


class SequencerProgrammingError(RuntimeError):
    pass


class SequenceNotStartedError(SequencerProgrammingError):
    """Raised when the sequence as been configured, but has not been started yet."""

    pass


class SequenceNotConfiguredError(SequencerProgrammingError):
    """Raised when the sequence has not been configured yet."""

    pass
