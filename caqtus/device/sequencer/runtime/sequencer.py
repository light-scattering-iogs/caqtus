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


def time_step_converter(value) -> TimeStep:
    return TimeStep(decimal.Decimal(value))


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
        converter=time_step_converter,
        validator=attrs.validators.gt(TimeStep(decimal.Decimal(0))),
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
    """A protocol that defines the interface to check the status of a sequence."""

    @abc.abstractmethod
    def is_finished(self) -> bool:
        raise NotImplementedError


class ProgrammedSequence(Protocol):
    """A protocol that defines the interface to start a sequence."""

    @abc.abstractmethod
    def run(self) -> contextlib.AbstractContextManager[SequenceStatus]:
        """Start the sequence.

        Returns:
            A context manager that can be used to start a sequence.

            The sequence must be started when the context manager is entered.
            The context manager must yield a status object that can be used to check
            the progress of the sequence.

            When the context manager is exited, the sequence should be stopped.
            The context manager must not be exited without error if the sequence is
            still running.
        """

        raise NotImplementedError
