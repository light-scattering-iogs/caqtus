from caqtus.device.sequencer.compilation import get_adaptive_clock
from caqtus.device.sequencer.instructions import Pattern


def test_0():
    target = Pattern([0, 1, 2, 3])

    pulse = Pattern([True]) * 10 + Pattern([False]) * 10

    clock = get_adaptive_clock(target, pulse)

    assert clock == pulse * len(target)
