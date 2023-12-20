import logging

from sequencer.channel import ChannelPattern, Repeat, Concatenate
from sequencer.instructions import ChannelLabel, SequencerInstruction

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def test_1():
    channel_1 = ChannelPattern([1, 2, 3, 4])
    sequence = SequencerInstruction.from_channel_instruction(ChannelLabel(1), channel_1)

    channel_2 = Repeat(ChannelPattern([5]), 4)
    sequence = sequence.add_channel_instruction(ChannelLabel(2), channel_2)

    assert sequence[ChannelLabel(1)].flatten() == channel_1.flatten()
    assert sequence[ChannelLabel(2)].flatten() == channel_2.flatten()


def test_2():
    channel_1 = Repeat(ChannelPattern([1]), 20)
    channel_2 = Repeat(ChannelPattern([2]), 20)
    channel_3 = Repeat(ChannelPattern([3, 4]), 10)

    sequence = SequencerInstruction.from_channel_instruction(ChannelLabel(1), channel_1)
    sequence = sequence.add_channel_instruction(ChannelLabel(2), channel_2)
    sequence = sequence.add_channel_instruction(ChannelLabel(3), channel_3)

    assert sequence[ChannelLabel(1)].flatten() == channel_1.flatten()
    assert sequence[ChannelLabel(2)].flatten() == channel_2.flatten()
    assert sequence[ChannelLabel(3)].flatten() == channel_3.flatten()


def test_3():
    channel_1 = Concatenate(
        [Repeat(ChannelPattern([1]), 20), Repeat(ChannelPattern([2]), 20)]
    )
    channel_2 = Concatenate(
        [Repeat(ChannelPattern([3]), 10), Repeat(ChannelPattern([4]), 30)]
    )

    sequence = SequencerInstruction.from_channel_instruction(ChannelLabel(1), channel_1)
    sequence = sequence.add_channel_instruction(ChannelLabel(2), channel_2)

    assert sequence[ChannelLabel(1)].flatten() == channel_1.flatten()
    assert sequence[ChannelLabel(2)].flatten() == channel_2.flatten()


def test_4():
    channel_1 = Repeat(ChannelPattern([1]), 10)
    channel_2 = Concatenate([ChannelPattern([1]), Repeat(ChannelPattern([2]), 9)])

    sequence = SequencerInstruction.from_channel_instruction(ChannelLabel(1), channel_1)
    sequence = sequence.add_channel_instruction(ChannelLabel(2), channel_2)

    assert sequence[ChannelLabel(1)].flatten() == channel_1.flatten()
    assert sequence[ChannelLabel(2)].flatten() == channel_2.flatten()


def test_5():
    channel_1 = Repeat(ChannelPattern([1]), 33)
    channel_2 = Concatenate(
        [Repeat(ChannelPattern([2]), 10), Repeat(ChannelPattern([3]), 23)]
    )

    sequence = SequencerInstruction.from_channel_instruction(ChannelLabel(1), channel_1)
    sequence = sequence.add_channel_instruction(ChannelLabel(2), channel_2)

    assert sequence[ChannelLabel(1)].flatten() == channel_1.flatten()
    assert sequence[ChannelLabel(2)].flatten() == channel_2.flatten()

    logger.debug(sequence)

    assert 0 == 1
