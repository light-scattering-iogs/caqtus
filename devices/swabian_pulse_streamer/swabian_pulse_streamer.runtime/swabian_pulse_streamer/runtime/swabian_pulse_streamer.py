from typing import Optional

from pulsestreamer import (
    PulseStreamer,
    TriggerStart,
    TriggerRearm,
    Sequence as PulseStreamerSequence,
)
from pydantic import validator

from sequencer.instructions import SequencerInstruction
from sequencer.runtime import (
    Sequencer,
    SequenceNotConfiguredError,
    Trigger,
)


class SwabianPulseStreamer(Sequencer):
    ip_address: str

    _pulse_streamer: PulseStreamer
    _sequence: Optional[PulseStreamerSequence] = None

    @validator("trigger")
    def _validate_trigger(cls, trigger: Trigger) -> Trigger:
        if not trigger.is_software_trigger():
            raise ValueError("Only supports software trigger.")
        return trigger

    def initialize(self) -> None:
        super().initialize()

        # There is no close method for the PulseStreamer class
        self._pulse_streamer = PulseStreamer(self.ip_address)
        if self.trigger.is_software_trigger():
            self._pulse_streamer.setTrigger(TriggerStart.SOFTWARE, TriggerRearm.MANUAL)
        else:
            raise ValueError("Only supports software trigger.")

    def update_parameters(self, *_, sequence: SequencerInstruction, **kwargs) -> None:
        super().update_parameters(*_, sequence=sequence, **kwargs)
        raise NotImplementedError("Not implemented yet.")

    def start_sequence(self) -> None:
        super().start_sequence()
        if not self._sequence:
            raise SequenceNotConfiguredError("The sequence has not been set yet.")
        self._pulse_streamer.stream(seq=self._sequence, n_runs=1)
        if self.trigger.is_software_trigger():
            self._pulse_streamer.startNow()

    def has_sequence_finished(self) -> bool:
        super().has_sequence_finished()
        return self._pulse_streamer.hasFinished()
