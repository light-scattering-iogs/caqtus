from __future__ import annotations

import abc
import contextlib
import decimal
from abc import ABC
from typing import ClassVar, Protocol

import attrs

from caqtus.device.runtime import Device
from .._time_step import TimeStep
from ..instructions import SequencerInstruction
from ..trigger import Trigger, is_trigger


@attrs.define(slots=False)
class Sequencer(Device, ABC):
    """Abstract base class for a sequencer device.

    This function defines the methods that a sequencer device must implement to be
    compatible with the caqtus framework.

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

    @trigger.validator  # type: ignore
    def _validate_trigger(self, _, value):
        if not is_trigger(value):
            raise ValueError(f"Invalid trigger {value}")

    @abc.abstractmethod
    def program_sequence(self, sequence: SequencerInstruction) -> ProgrammedSequence:
        """Program the sequence into the device.

        This method just writes the sequence to the device. It does not start the
        sequence.

        Args:
            sequence: The sequence to be programmed into the sequencer.

        Returns:
            An object that can be used to start the sequence.
        """

        raise NotImplementedError


class SequenceStatus(Protocol):
    @abc.abstractmethod
    def is_finished(self) -> bool:
        raise NotImplementedError


class ProgrammedSequence(Protocol):
    @abc.abstractmethod
    def run(self) -> contextlib.AbstractContextManager[SequenceStatus]:
        raise NotImplementedError


class SequencerProgrammingError(RuntimeError):
    pass


class SequenceNotStartedError(SequencerProgrammingError):
    """Raised when the sequence as been configured, but has not been started yet."""

    pass


class SequenceNotConfiguredError(SequencerProgrammingError):
    """Raised when the sequence has not been configured yet."""

    pass
