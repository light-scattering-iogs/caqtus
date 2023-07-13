from pulsestreamer import PulseStreamer, Sequence

from sequencer.runtime.sequencer import Sequencer


class SwabianPulseStreamer(Sequencer):
    ip_address: str

    _pulse_streamer: PulseStreamer

    def initialize(self) -> None:
        super().initialize()

        # There is no close method for the PulseStreamer class
        self._pulse_streamer = PulseStreamer(self.ip_address)

    def update_parameters(self, *_, sequence: Sequence, **kwargs) -> None:
        raise NotImplementedError
