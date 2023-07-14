from sequencer.channel import (
    ChannelPattern,
    Repeat as ChannelRepeat,
    Concatenate as ChannelConcatenate,
)
from sequencer.instructions import Concatenate, Repeat, SequencerPattern

channel_label = 14
sequence = Concatenate(
    (
        Repeat(
            SequencerPattern(
                {
                    0: ChannelPattern((True,)),
                    1: ChannelPattern((False,)),
                    2: ChannelPattern((True,)),
                    3: ChannelPattern((False,)),
                    4: ChannelPattern((True,)),
                    5: ChannelPattern((False,)),
                    6: ChannelPattern((True,)),
                    7: ChannelPattern((True,)),
                    8: ChannelPattern((True,)),
                    9: ChannelPattern((False,)),
                    10: ChannelPattern((True,)),
                    11: ChannelPattern((False,)),
                    12: ChannelPattern((False,)),
                    13: ChannelPattern((True,)),
                }
            ),
            25,
        ),
        Repeat(
            SequencerPattern(
                {
                    0: ChannelPattern((False,)),
                    1: ChannelPattern((False,)),
                    2: ChannelPattern((True,)),
                    3: ChannelPattern((False,)),
                    4: ChannelPattern((True,)),
                    5: ChannelPattern((False,)),
                    6: ChannelPattern((True,)),
                    7: ChannelPattern((True,)),
                    8: ChannelPattern((True,)),
                    9: ChannelPattern((False,)),
                    10: ChannelPattern((True,)),
                    11: ChannelPattern((False,)),
                    12: ChannelPattern((False,)),
                    13: ChannelPattern((True,)),
                }
            ),
            25,
        ),
        Repeat(
            SequencerPattern(
                {
                    0: ChannelPattern((False,)),
                    1: ChannelPattern((False,)),
                    2: ChannelPattern((True,)),
                    3: ChannelPattern((False,)),
                    4: ChannelPattern((True,)),
                    5: ChannelPattern((False,)),
                    6: ChannelPattern((True,)),
                    7: ChannelPattern((True,)),
                    8: ChannelPattern((True,)),
                    9: ChannelPattern((False,)),
                    10: ChannelPattern((True,)),
                    11: ChannelPattern((False,)),
                    12: ChannelPattern((False,)),
                    13: ChannelPattern((True,)),
                }
            ),
            166617,
        ),
        Repeat(
            SequencerPattern(
                {
                    0: ChannelPattern((False,)),
                    1: ChannelPattern((False,)),
                    2: ChannelPattern((False,)),
                    3: ChannelPattern((False,)),
                    4: ChannelPattern((False,)),
                    5: ChannelPattern((False,)),
                    6: ChannelPattern((True,)),
                    7: ChannelPattern((True,)),
                    8: ChannelPattern((False,)),
                    9: ChannelPattern((False,)),
                    10: ChannelPattern((False,)),
                    11: ChannelPattern((False,)),
                    12: ChannelPattern((False,)),
                    13: ChannelPattern((True,)),
                }
            ),
            33,
        ),
        Repeat(
            Concatenate(
                (
                    Repeat(
                        SequencerPattern(
                            {
                                0: ChannelPattern((True,)),
                                1: ChannelPattern((False,)),
                                2: ChannelPattern((False,)),
                                3: ChannelPattern((False,)),
                                4: ChannelPattern((False,)),
                                5: ChannelPattern((False,)),
                                6: ChannelPattern((True,)),
                                7: ChannelPattern((True,)),
                                8: ChannelPattern((False,)),
                                9: ChannelPattern((False,)),
                                10: ChannelPattern((False,)),
                                11: ChannelPattern((False,)),
                                12: ChannelPattern((False,)),
                                13: ChannelPattern((True,)),
                            }
                        ),
                        25,
                    ),
                    Repeat(
                        SequencerPattern(
                            {
                                0: ChannelPattern((False,)),
                                1: ChannelPattern((False,)),
                                2: ChannelPattern((False,)),
                                3: ChannelPattern((False,)),
                                4: ChannelPattern((False,)),
                                5: ChannelPattern((False,)),
                                6: ChannelPattern((True,)),
                                7: ChannelPattern((True,)),
                                8: ChannelPattern((False,)),
                                9: ChannelPattern((False,)),
                                10: ChannelPattern((False,)),
                                11: ChannelPattern((False,)),
                                12: ChannelPattern((False,)),
                                13: ChannelPattern((True,)),
                            }
                        ),
                        25,
                    ),
                )
            ),
            26666,
        ),
        Repeat(
            SequencerPattern(
                {
                    0: ChannelPattern((True,)),
                    1: ChannelPattern((False,)),
                    2: ChannelPattern((False,)),
                    3: ChannelPattern((False,)),
                    4: ChannelPattern((True,)),
                    5: ChannelPattern((False,)),
                    6: ChannelPattern((True,)),
                    7: ChannelPattern((True,)),
                    8: ChannelPattern((False,)),
                    9: ChannelPattern((False,)),
                    10: ChannelPattern((False,)),
                    11: ChannelPattern((False,)),
                    12: ChannelPattern((False,)),
                    13: ChannelPattern((True,)),
                }
            ),
            25,
        ),
        Repeat(
            SequencerPattern(
                {
                    0: ChannelPattern((False,)),
                    1: ChannelPattern((False,)),
                    2: ChannelPattern((False,)),
                    3: ChannelPattern((False,)),
                    4: ChannelPattern((True,)),
                    5: ChannelPattern((False,)),
                    6: ChannelPattern((True,)),
                    7: ChannelPattern((True,)),
                    8: ChannelPattern((False,)),
                    9: ChannelPattern((False,)),
                    10: ChannelPattern((False,)),
                    11: ChannelPattern((False,)),
                    12: ChannelPattern((False,)),
                    13: ChannelPattern((True,)),
                }
            ),
            25,
        ),
        Repeat(
            SequencerPattern(
                {
                    0: ChannelPattern((False,)),
                    1: ChannelPattern((False,)),
                    2: ChannelPattern((False,)),
                    3: ChannelPattern((False,)),
                    4: ChannelPattern((True,)),
                    5: ChannelPattern((False,)),
                    6: ChannelPattern((True,)),
                    7: ChannelPattern((True,)),
                    8: ChannelPattern((False,)),
                    9: ChannelPattern((False,)),
                    10: ChannelPattern((False,)),
                    11: ChannelPattern((False,)),
                    12: ChannelPattern((False,)),
                    13: ChannelPattern((True,)),
                }
            ),
            2499950,
        ),
        Repeat(
            SequencerPattern(
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
                    13: ChannelPattern((True,)),
                }
            ),
            25,
        ),
        Repeat(
            SequencerPattern(
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
                    13: ChannelPattern((True,)),
                }
            ),
            25,
        ),
        Repeat(
            SequencerPattern(
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
                    13: ChannelPattern((True,)),
                }
            ),
            16617,
        ),
        Repeat(
            SequencerPattern(
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
                    12: ChannelPattern((True,)),
                    13: ChannelPattern((False,)),
                }
            ),
            33,
        ),
        Repeat(
            Concatenate(
                (
                    Repeat(
                        SequencerPattern(
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
                                12: ChannelPattern((True,)),
                                13: ChannelPattern((False,)),
                            }
                        ),
                        25,
                    ),
                    Repeat(
                        SequencerPattern(
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
                                12: ChannelPattern((True,)),
                                13: ChannelPattern((False,)),
                            }
                        ),
                        25,
                    ),
                )
            ),
            9999,
        ),
        Repeat(
            SequencerPattern(
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
                    12: ChannelPattern((True,)),
                    13: ChannelPattern((False,)),
                }
            ),
            17,
        ),
        Repeat(
            SequencerPattern(
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
            ),
            8,
        ),
        Repeat(
            SequencerPattern(
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
            ),
            25,
        ),
        Repeat(
            Concatenate(
                (
                    Repeat(
                        SequencerPattern(
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
                        ),
                        25,
                    ),
                    Repeat(
                        SequencerPattern(
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
                        ),
                        25,
                    ),
                )
            ),
            3332,
        ),
        Repeat(
            SequencerPattern(
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
            ),
            25,
        ),
        Repeat(
            SequencerPattern(
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
            ),
            9,
        ),
        Repeat(
            SequencerPattern(
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
            ),
            16,
        ),
        Repeat(
            SequencerPattern(
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
            ),
            25,
        ),
        Repeat(
            SequencerPattern(
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
            ),
            25,
        ),
        Repeat(
            SequencerPattern(
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
            ),
            166600,
        ),
        Repeat(
            SequencerPattern(
                {
                    0: ChannelPattern((True,)),
                    1: ChannelPattern((False,)),
                    2: ChannelPattern((False,)),
                    3: ChannelPattern((False,)),
                    4: ChannelPattern((True,)),
                    5: ChannelPattern((True,)),
                    6: ChannelPattern((False,)),
                    7: ChannelPattern((False,)),
                    8: ChannelPattern((False,)),
                    9: ChannelPattern((False,)),
                    10: ChannelPattern((False,)),
                    11: ChannelPattern((False,)),
                    12: ChannelPattern((True,)),
                    13: ChannelPattern((False,)),
                }
            ),
            25,
        ),
        Repeat(
            SequencerPattern(
                {
                    0: ChannelPattern((False,)),
                    1: ChannelPattern((False,)),
                    2: ChannelPattern((False,)),
                    3: ChannelPattern((False,)),
                    4: ChannelPattern((True,)),
                    5: ChannelPattern((True,)),
                    6: ChannelPattern((False,)),
                    7: ChannelPattern((False,)),
                    8: ChannelPattern((False,)),
                    9: ChannelPattern((False,)),
                    10: ChannelPattern((False,)),
                    11: ChannelPattern((False,)),
                    12: ChannelPattern((True,)),
                    13: ChannelPattern((False,)),
                }
            ),
            25,
        ),
        Repeat(
            SequencerPattern(
                {
                    0: ChannelPattern((False,)),
                    1: ChannelPattern((False,)),
                    2: ChannelPattern((False,)),
                    3: ChannelPattern((False,)),
                    4: ChannelPattern((True,)),
                    5: ChannelPattern((True,)),
                    6: ChannelPattern((False,)),
                    7: ChannelPattern((False,)),
                    8: ChannelPattern((False,)),
                    9: ChannelPattern((False,)),
                    10: ChannelPattern((False,)),
                    11: ChannelPattern((False,)),
                    12: ChannelPattern((True,)),
                    13: ChannelPattern((False,)),
                }
            ),
            499951,
        ),
        Repeat(
            SequencerPattern(
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
            ),
            49,
        ),
        Repeat(
            SequencerPattern(
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
            ),
            25,
        ),
        Repeat(
            SequencerPattern(
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
            ),
            25,
        ),
        Repeat(
            SequencerPattern(
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
            ),
            499901,
        ),
        Repeat(
            SequencerPattern(
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
                    12: ChannelPattern((True,)),
                    13: ChannelPattern((False,)),
                }
            ),
            49,
        ),
        Repeat(
            SequencerPattern(
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
                    12: ChannelPattern((True,)),
                    13: ChannelPattern((False,)),
                }
            ),
            25,
        ),
        Repeat(
            SequencerPattern(
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
                    12: ChannelPattern((True,)),
                    13: ChannelPattern((False,)),
                }
            ),
            25,
        ),
        Repeat(
            SequencerPattern(
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
                    12: ChannelPattern((True,)),
                    13: ChannelPattern((False,)),
                }
            ),
            499901,
        ),
        Repeat(
            SequencerPattern(
                {
                    0: ChannelPattern((False,)),
                    1: ChannelPattern((False,)),
                    2: ChannelPattern((False,)),
                    3: ChannelPattern((False,)),
                    4: ChannelPattern((False,)),
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
            ),
            49,
        ),
        Repeat(
            SequencerPattern(
                {
                    0: ChannelPattern((True,)),
                    1: ChannelPattern((False,)),
                    2: ChannelPattern((False,)),
                    3: ChannelPattern((False,)),
                    4: ChannelPattern((False,)),
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
            ),
            25,
        ),
        Repeat(
            SequencerPattern(
                {
                    0: ChannelPattern((False,)),
                    1: ChannelPattern((False,)),
                    2: ChannelPattern((False,)),
                    3: ChannelPattern((False,)),
                    4: ChannelPattern((False,)),
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
            ),
            25,
        ),
        Repeat(
            SequencerPattern(
                {
                    0: ChannelPattern((False,)),
                    1: ChannelPattern((False,)),
                    2: ChannelPattern((False,)),
                    3: ChannelPattern((False,)),
                    4: ChannelPattern((False,)),
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
            ),
            16567,
        ),
        Repeat(
            SequencerPattern(
                {
                    0: ChannelPattern((False,)),
                    1: ChannelPattern((False,)),
                    2: ChannelPattern((True,)),
                    3: ChannelPattern((False,)),
                    4: ChannelPattern((True,)),
                    5: ChannelPattern((False,)),
                    6: ChannelPattern((True,)),
                    7: ChannelPattern((True,)),
                    8: ChannelPattern((True,)),
                    9: ChannelPattern((False,)),
                    10: ChannelPattern((True,)),
                    11: ChannelPattern((True,)),
                    12: ChannelPattern((False,)),
                    13: ChannelPattern((True,)),
                }
            ),
            33,
        ),
        Repeat(
            SequencerPattern(
                {
                    0: ChannelPattern((True,)),
                    1: ChannelPattern((False,)),
                    2: ChannelPattern((True,)),
                    3: ChannelPattern((False,)),
                    4: ChannelPattern((True,)),
                    5: ChannelPattern((False,)),
                    6: ChannelPattern((True,)),
                    7: ChannelPattern((True,)),
                    8: ChannelPattern((True,)),
                    9: ChannelPattern((False,)),
                    10: ChannelPattern((True,)),
                    11: ChannelPattern((True,)),
                    12: ChannelPattern((False,)),
                    13: ChannelPattern((True,)),
                }
            ),
            25,
        ),
        Repeat(
            SequencerPattern(
                {
                    0: ChannelPattern((False,)),
                    1: ChannelPattern((False,)),
                    2: ChannelPattern((True,)),
                    3: ChannelPattern((False,)),
                    4: ChannelPattern((True,)),
                    5: ChannelPattern((False,)),
                    6: ChannelPattern((True,)),
                    7: ChannelPattern((True,)),
                    8: ChannelPattern((True,)),
                    9: ChannelPattern((False,)),
                    10: ChannelPattern((True,)),
                    11: ChannelPattern((True,)),
                    12: ChannelPattern((False,)),
                    13: ChannelPattern((True,)),
                }
            ),
            25,
        ),
        Repeat(
            SequencerPattern(
                {
                    0: ChannelPattern((False,)),
                    1: ChannelPattern((False,)),
                    2: ChannelPattern((True,)),
                    3: ChannelPattern((False,)),
                    4: ChannelPattern((True,)),
                    5: ChannelPattern((False,)),
                    6: ChannelPattern((True,)),
                    7: ChannelPattern((True,)),
                    8: ChannelPattern((True,)),
                    9: ChannelPattern((False,)),
                    10: ChannelPattern((True,)),
                    11: ChannelPattern((True,)),
                    12: ChannelPattern((False,)),
                    13: ChannelPattern((True,)),
                }
            ),
            166584,
        ),
    )
)
blink_instruction = ChannelConcatenate(
    (
        ChannelRepeat(ChannelPattern((False,)), 166667),
        ChannelRepeat(ChannelPattern((False,)), 1333333),
        ChannelRepeat(ChannelPattern((True,)), 2500000),
        ChannelRepeat(ChannelPattern((True,)), 16667),
        ChannelRepeat(ChannelPattern((True,)), 500000),
        ChannelRepeat(
            ChannelConcatenate((ChannelPattern((True,)), ChannelPattern((False,)))), 83333
        ),
        ChannelPattern((False,)),
        ChannelRepeat(ChannelPattern((True,)), 666667),
        ChannelRepeat(ChannelPattern((True,)), 500000),
        ChannelRepeat(ChannelPattern((True,)), 500000),
        ChannelRepeat(ChannelPattern((False,)), 16666),
        ChannelRepeat(ChannelPattern((True,)), 166667),
    )
)
