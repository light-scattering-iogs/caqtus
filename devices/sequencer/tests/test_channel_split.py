import numpy as np

from sequencer.channel import ChannelInstruction, Concatenate, Repeat, ChannelPattern


def assert_split_valid(instruction: ChannelInstruction):
    for split_index in range(0, len(instruction)):
        a, b = instruction.split(split_index)

        if a.is_empty():
            assert split_index == 0, f"{instruction=},{len(instruction)=}, {split_index=}"
        else:
            assert np.array_equal(
                a.flatten().values, instruction.flatten().values[:split_index]
            )

        if b.is_empty():
            assert split_index == len(instruction)
        else:
            assert np.array_equal(
                b.flatten().values, instruction.flatten().values[split_index:]
            )


def test_consecutive_split():
    pattern_1 = ChannelPattern([1, 2, 3, 4])
    pattern_2 = ChannelPattern([5])
    pattern_3 = ChannelPattern([9, 10, 11, 12])

    sequence = Concatenate([pattern_1, pattern_2, pattern_3])
    assert_split_valid(sequence)

    repeat = Repeat(sequence, 3)
    sequence = Concatenate([repeat, repeat, repeat])
    assert_split_valid(sequence)


def test_pattern_split():
    pattern = ChannelPattern([1, 2, 3, 4])
    assert_split_valid(pattern)

    pattern = ChannelPattern([1, 2, 3, 4, 5])
    assert_split_valid(pattern)

    pattern = ChannelPattern([1, 2])
    assert_split_valid(pattern)


def test_repeat_split():
    pattern = ChannelPattern([1, 2])
    repeat = Repeat(pattern, 3)
    assert_split_valid(repeat)

    sequence = Concatenate([pattern, pattern, pattern])
    repeat = Repeat(sequence, 3)
    assert_split_valid(repeat)
