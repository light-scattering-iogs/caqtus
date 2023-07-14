from sequencer.channel import (
    ChannelPattern,
)
from sequencer.instructions import SequencerPattern

p0 = SequencerPattern(
    {
        0: ChannelPattern((True,)),
        1: ChannelPattern((False,)),
        2: ChannelPattern((False,)),
        3: ChannelPattern((False,)),
        4: ChannelPattern((True,)),
        5: ChannelPattern((False,)),
        6: ChannelPattern((False,)),
        7: ChannelPattern((False,)),
        8: ChannelPattern((False,)),
        9: ChannelPattern((False,)),
        10: ChannelPattern((False,)),
        11: ChannelPattern((False,)),
        12: ChannelPattern((False,)),
        13: ChannelPattern((False,)),
    }
)
p1 = SequencerPattern(
    {
        0: ChannelPattern((False,)),
        1: ChannelPattern((False,)),
        2: ChannelPattern((False,)),
        3: ChannelPattern((False,)),
        4: ChannelPattern((True,)),
        5: ChannelPattern((False,)),
        6: ChannelPattern((False,)),
        7: ChannelPattern((False,)),
        8: ChannelPattern((False,)),
        9: ChannelPattern((False,)),
        10: ChannelPattern((False,)),
        11: ChannelPattern((False,)),
        12: ChannelPattern((False,)),
        13: ChannelPattern((False,)),
    }
)


c1 = ChannelPattern((True,))
c0 = ChannelPattern((False,))

channel_label = 14
sequence = (p0 * 25 + p1 * 25) * 3332
blink_instruction = c0 + (c1 + c0) * 83299 + c0
