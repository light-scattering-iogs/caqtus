import numpy as np

from sequencer.time_sequence import TimeSequence
from sequencer.time_sequence_instructions import Pattern


def test_time_sequence():
    sequence = TimeSequence(time_step=1e-9)

    steps_1 = Pattern(durations=[1, 2, 3])
    steps_1.append_channel([True, False, True])
    steps_1.append_channel([1, 2, 3])
    steps_1.append_channel([0.7, 2.5, -3])
    sequence.append_instruction(steps_1)

    steps_2 = Pattern(durations=[4, 5, 6])
    steps_2.append_channel([False, True, False])
    steps_2.append_channel([4, 5, 6])
    steps_2.append_channel([-0.7, 2.5, -3])
    sequence.append_instruction(steps_2)

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
