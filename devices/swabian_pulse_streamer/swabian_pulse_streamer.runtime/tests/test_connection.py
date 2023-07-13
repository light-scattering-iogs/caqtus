from sequencer.channel import ChannelPattern
from sequencer.instructions import SequencerPattern, ChannelLabel
from swabian_pulse_streamer.runtime.swabian_pulse_streamer import SwabianPulseStreamer


def test_connection():
    pulse_streamer = SwabianPulseStreamer(
        name="pulse streamer", ip_address="192.168.137.187", time_step=1
    )

    channel_pattern = ChannelPattern([i % 2 for i in range(30)])
    sequence = SequencerPattern.from_channel_instruction(
        ChannelLabel(0), channel_pattern
    )

    for channel in range(1, pulse_streamer.channel_number):
        channel_pattern = ChannelPattern([(i // channel) % 2 for i in range(30)])
        sequence = sequence.add_channel_instruction(
            ChannelLabel(channel), channel_pattern
        )

    with pulse_streamer:
        pulse_streamer.update_parameters(sequence=sequence)
        pulse_streamer._sequence.plot()
