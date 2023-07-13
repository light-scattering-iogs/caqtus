import logging

from sequencer.channel import ChannelPattern
from sequencer.instructions import SequencerPattern, ChannelLabel
from swabian_pulse_streamer.runtime.swabian_pulse_streamer import SwabianPulseStreamer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# This test requires a Pulse Streamer to be connected to the computer running the test, with the IP address below.
IP_ADDRESS = "192.168.137.187"


def test_pulse_streamer():
    pulse_streamer = SwabianPulseStreamer(
        name="pulse streamer", ip_address=IP_ADDRESS, time_step=1
    )

    channel_0_pattern = ChannelPattern([(i // 7) % 2 for i in range(30)])
    sequence = SequencerPattern.from_channel_instruction(
        ChannelLabel(0), channel_0_pattern
    )

    channel_1_pattern = (
        ChannelPattern([i % 2 for i in range(15)]) + ChannelPattern([0]) * 15
    )
    sequence = sequence.add_channel_instruction(ChannelLabel(1), channel_1_pattern)

    channel_2_pattern = (
        ChannelPattern([0]) * 12 + ChannelPattern([1]) * 6 + ChannelPattern([0]) * 12
    )
    sequence = sequence.add_channel_instruction(ChannelLabel(2), channel_2_pattern)

    channel_3_pattern = ChannelPattern([0, 1, 1, 0]) * 3 + ChannelPattern([1]) * 18
    sequence = sequence.add_channel_instruction(ChannelLabel(3), channel_3_pattern)

    channel_pattern = ChannelPattern([0 for i in range(30)])
    for channel in range(4, pulse_streamer.channel_number):
        sequence = sequence.add_channel_instruction(
            ChannelLabel(channel), channel_pattern
        )

    with pulse_streamer:
        pulse_streamer.update_parameters(sequence=sequence)

    expected_result = [
        (1, 0, 0, 0),
        (1, 10, 0, 0),
        (1, 8, 0, 0),
        (1, 2, 0, 0),
        (1, 0, 0, 0),
        (1, 10, 0, 0),
        (1, 8, 0, 0),
        (1, 3, 0, 0),
        (1, 1, 0, 0),
        (1, 11, 0, 0),
        (1, 9, 0, 0),
        (1, 3, 0, 0),
        (1, 13, 0, 0),
        (1, 15, 0, 0),
        (4, 12, 0, 0),
        (3, 8, 0, 0),
        (7, 9, 0, 0),
        (2, 8, 0, 0),
    ]

    assert pulse_streamer._sequence.getData() == expected_result, "Sequence is wrong."
