import pytest

from sequencer.channel_instruction import (
    Pattern,
    ConsecutiveInstructions,
    ChannelInstruction,
    Repeat,
)


def assert_split_valid(instruction: ChannelInstruction):
    with pytest.raises(ValueError):
        instruction.split(0)

    with pytest.raises(ValueError):
        instruction.split(len(instruction))

    for split_index in range(1, len(instruction)):
        a, b = instruction.split(split_index)
        assert len(a) == split_index, f"len({a=}) != {split_index=}"
        assert len(b) == len(instruction) - split_index


def test_consecutive_split():
    pattern_1 = Pattern([1, 2, 3, 4])
    pattern_2 = Pattern([5])
    pattern_3 = Pattern([9, 10, 11, 12])

    sequence = ConsecutiveInstructions([pattern_1, pattern_2, pattern_3])
    assert_split_valid(sequence)

    repeat = Repeat(sequence, 3)
    sequence = ConsecutiveInstructions([repeat, repeat, repeat])
    assert_split_valid(sequence)


def test_pattern_split():
    pattern = Pattern([1, 2, 3, 4])
    assert_split_valid(pattern)

    pattern = Pattern([1, 2, 3, 4, 5])
    assert_split_valid(pattern)

    pattern = Pattern([1, 2])
    assert_split_valid(pattern)


def test_repeat_split():
    pattern = Pattern([1, 2])
    repeat = Repeat(pattern, 3)
    assert_split_valid(repeat)

    sequence = ConsecutiveInstructions([pattern, pattern, pattern])
    repeat = Repeat(sequence, 3)
    assert_split_valid(repeat)
