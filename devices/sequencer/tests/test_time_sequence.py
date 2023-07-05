from sequencer.channel_name import ChannelName
from sequencer.time_sequence import TimeSequence
from sequencer.time_sequence_instructions import Steps


def test_time_sequence():
    sequence = TimeSequence(time_step=1e-9)

    steps_1 = Steps(durations=[1, 2, 3])
    steps_1.add_channel_values(ChannelName("ch1"), [1, 2, 3])
    steps_1.add_channel_values(ChannelName("ch2"), [4, 5, 6])
    sequence.append_instruction(steps_1)

    steps_2 = Steps(durations=[4, 5, 6])
    steps_2.add_channel_values(ChannelName("ch1"), [7, 8, 9])
    steps_2.add_channel_values(ChannelName("ch2"), [10, 11, 12])
    sequence.append_instruction(steps_2)

    assert sequence.duration() == 21
    assert sequence.channel_dtypes == {"ch1": int, "ch2": int}
