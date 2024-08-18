import decimal
from abc import ABC, abstractmethod
from typing import ClassVar

import attrs

from caqtus.device.runtime import Device
from .._time_step import TimeStep
from ..instructions import SequencerInstruction
from ..trigger import Trigger, is_trigger


@attrs.define(slots=False)
class Sequencer(Device, ABC):
    """Base class for all sequencers.

    Attributes:
        time_step: The time step of the sequencer in nanoseconds.
            This value cannot be changed after the sequencer has been created.
        trigger: Indicates how the sequence is started and how it is clocked.
            This value cannot be changed after the sequencer has been created.
    """

    channel_number: ClassVar[int]

    time_step: TimeStep = attrs.field(
        on_setattr=attrs.setters.frozen,
        converter=decimal.Decimal,
        validator=attrs.validators.gt(decimal.Decimal(0)),
    )
    trigger: Trigger = attrs.field(
        on_setattr=attrs.setters.frozen,
    )

    _sequence_programmed: bool = attrs.field(default=False, init=False)
    _sequence_started: bool = attrs.field(default=False, init=False)

    @trigger.validator  # type: ignore
    def _validate_trigger(self, _, value):
        if not is_trigger(value):
            raise ValueError(f"Invalid trigger {value}")

    @abstractmethod
    def update_parameters(
        self, sequence: SequencerInstruction, *args, **kwargs
    ) -> None:
        """Update the parameters of the sequencer.

        Args:
            sequence: The sequence to be programmed into the sequencer.
        """

        if sequence.width != self.channel_number:
            raise ValueError(
                f"Invalid number of channels, expected {self.channel_number} but got"
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


class SequencerProgrammingError(RuntimeError):
    pass


class SequenceNotStartedError(SequencerProgrammingError):
    """Raised when the sequence as been configured, but has not been started yet."""

    pass


class SequenceNotConfiguredError(SequencerProgrammingError):
    """Raised when the sequence has not been configured yet."""

    pass
