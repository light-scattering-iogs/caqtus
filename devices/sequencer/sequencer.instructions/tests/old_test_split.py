import logging

from sequencer.channel import ChannelPattern, Repeat as ChannelRepeat
from sequencer.instructions import Repeat, SequencerPattern, ChannelLabel

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def test_split():
    part = ChannelRepeat(ChannelPattern((3,)), 10)
    instruction = Repeat(SequencerPattern({ChannelLabel(1): ChannelPattern((1,))}), 20)

    left, right = instruction.split(len(part))
    logger.debug(f"{left=}")
    logger.debug(f"{right=}")
    assert len(left) == len(part)
    assert len(right) == len(instruction) - len(part)
    assert right == Repeat(SequencerPattern({ChannelLabel(1): ChannelPattern((1,))}), 10)
