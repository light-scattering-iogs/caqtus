from sequencer.channel import ChannelPattern, Concatenate, Repeat
from sequencer.instructions import SequencerInstruction, ChannelLabel


def test_blink():
    sequencer = SequencerInstruction.from_channel_instruction(
        ChannelLabel(0), ChannelPattern((True,)) * 166667
    )

    blink = Concatenate(
        (
            Repeat(
                Concatenate(
                    (
                        Repeat(ChannelPattern((True,)), 8),
                        Repeat(ChannelPattern((False,)), 8),
                    )
                ),
                10416,
            ),
            Repeat(ChannelPattern((False,)), 11),
        )
    )

    sequencer.add_channel_instruction(ChannelLabel(1), blink)
