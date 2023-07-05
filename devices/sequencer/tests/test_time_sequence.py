import numpy as np

from sequencer.channel_config import ChannelConfig
from sequencer.time_sequence import TimeSequence


def test_time_sequence():
    channel_configs = [
        ChannelConfig[bool](
            default_value=False, initial_value=False, final_value=False
        ),
        ChannelConfig[int](default_value=0, initial_value=0, final_value=0),
        ChannelConfig[float](default_value=0.0, initial_value=0.0, final_value=0.0),
    ]

    sequence = TimeSequence(time_step=1e-9, channel_configs=channel_configs)

    pattern = sequence.append_new_pattern([1, 2, 3])
    pattern.set_values(0, [True, False, True])
    pattern.set_values(1, [1, 2, 3])
    pattern.set_values(2, [0.7, 2.5, -3])

    pattern_2 = sequence.append_new_pattern([4, 5, 6])
    pattern_2.set_values(0, [False, True, False])
    pattern_2.set_values(1, [4, 5, 6])
    pattern_2.set_values(2, [-0.7, 2.5, -3])

    assert sequence.total_duration() == 21
    for a, b in zip(
        sequence.unroll().channel_values,
        (
            np.array([True, False, True, False, True, False]),
            np.array([1, 2, 3, 4, 5, 6]),
            np.array([0.7, 2.5, -3, -0.7, 2.5, -3]),
        ),
    ):
        assert np.array_equal(a, b)

    sequence.apply(0, np.logical_not)
    assert np.array_equal(
        sequence.unroll().channel_values[0],
        np.array([False, True, False, True, False, True]),
    )
