import logging
from functools import singledispatchmethod
from typing import Optional, ClassVar

from attr.validators import instance_of, ge, le
from attrs import define, field
from attrs.setters import frozen
from pulsestreamer import (
    PulseStreamer,
    TriggerStart,
    TriggerRearm,
    Sequence as PulseStreamerSequence,
    OutputState,
)

from sequencer.instructions.struct_array_instruction import (
    SequencerInstruction,
    Pattern,
    Concatenate,
    Repeat,
)
from sequencer.runtime import (
    Sequencer,
    SequenceNotConfiguredError,
    Trigger,
    ExternalTriggerStart,
    TriggerEdge,
)

logger = logging.getLogger(__name__)

logger.setLevel(logging.DEBUG)


@define(slots=False)
class SwabianPulseStreamer(Sequencer):
    # only support digital channels at the moment
    channel_number: ClassVar[int] = 8

    ip_address: str = field(validator=instance_of(str), on_setattr=frozen)
    # only 1 ns time step supported
    time_step: int = field(validator=[ge(1), le(1)], on_setattr=frozen)

    trigger: Trigger = field(
        factory=lambda: ExternalTriggerStart(edge=TriggerEdge.RISING),
        validator=instance_of(Trigger),
        on_setattr=frozen,
    )

    _pulse_streamer: PulseStreamer = field(init=False)
    _sequence: Optional[PulseStreamerSequence] = field(default=None, init=False)

    @trigger.validator  # type: ignore
    def _validate_trigger(self, attribute, value):
        if not (value.is_software_trigger() or isinstance(value, ExternalTriggerStart)):
            raise ValueError("Only supports software or external trigger start.")
        return value

    def initialize(self) -> None:
        super().initialize()

        # There is no close method for the PulseStreamer class
        self._pulse_streamer = PulseStreamer(self.ip_address)
        self.setup_trigger()

    def setup_trigger(self) -> None:
        if self.trigger.is_software_trigger():
            start = TriggerStart.SOFTWARE
        elif isinstance(self.trigger, ExternalTriggerStart):
            if self.trigger.edge == TriggerEdge.RISING:
                start = TriggerStart.HARDWARE_RISING
            elif self.trigger.edge == TriggerEdge.FALLING:
                start = TriggerStart.HARDWARE_FALLING
            else:
                raise ValueError("Only supports rising or falling edge.")
        else:
            raise ValueError("Only supports software trigger.")
        self._pulse_streamer.setTrigger(start, TriggerRearm.MANUAL)

    def update_parameters(self, *_, sequence: SequencerInstruction, **kwargs) -> None:
        super().update_parameters(sequence=sequence, **kwargs)
        self._sequence = self._construct_pulse_streamer_sequence(sequence)
        last_values = sequence[-1]
        enabled_output = [
            channel
            for channel in range(self.channel_number)
            if last_values[f"ch {channel}"]
        ]
        logger.debug(last_values)
        self._final_state = OutputState(enabled_output, 0.0, 0.0)
        self._set_sequence_programmed()

    def start_sequence(self) -> None:
        super().start_sequence()
        if not self._sequence:
            raise SequenceNotConfiguredError("The sequence has not been set yet.")
        self._pulse_streamer.stream(
            seq=self._sequence, n_runs=1, final=self._final_state
        )
        if self.trigger.is_software_trigger():
            self._pulse_streamer.startNow()

    def has_sequence_finished(self) -> bool:
        super().has_sequence_finished()
        return self._pulse_streamer.hasFinished()

    @singledispatchmethod
    def _construct_pulse_streamer_sequence(
        self, instruction: SequencerInstruction
    ) -> PulseStreamerSequence:
        raise NotImplementedError(
            f"Not implemented for type of instruction {type(instruction)}."
        )

    @_construct_pulse_streamer_sequence.register
    def _(self, pattern: Pattern) -> PulseStreamerSequence:
        sequence = self._pulse_streamer.createSequence()
        values = pattern.array
        for channel in range(self.channel_number):
            channel_values = values[f"ch {channel}"]
            sequence.setDigital(channel, [(1, v) for v in channel_values])
        return sequence

    @_construct_pulse_streamer_sequence.register
    def _(self, concatenate: Concatenate) -> PulseStreamerSequence:
        instructions = concatenate.instructions
        seq = self._construct_pulse_streamer_sequence(instructions[0])
        for instruction in instructions[1:]:
            seq += self._construct_pulse_streamer_sequence(instruction)
        return seq

    @_construct_pulse_streamer_sequence.register
    def _(self, repeat: Repeat) -> PulseStreamerSequence:
        if len(repeat.instruction) == 1:
            channel_values = repeat.instruction[0]
            seq = self._pulse_streamer.createSequence()
            for channel in range(self.channel_number):
                seq.setDigital(
                    channel,
                    [
                        (
                            repeat.repetitions,
                            channel_values[f"ch {channel}"],
                        )
                    ],
                )
            return seq
        else:
            return (
                self._construct_pulse_streamer_sequence(repeat.instruction)
                * repeat.repetitions
            )
