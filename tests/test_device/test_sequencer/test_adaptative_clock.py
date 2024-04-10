import pytest

from caqtus.device.sequencer.compilation import get_adaptive_clock
from caqtus.device.sequencer.instructions import Pattern, stack_instructions, with_name


def test_0():
    target = Pattern([0, 1, 2, 3])

    pulse = Pattern([True]) * 10 + Pattern([False]) * 10

    clock = get_adaptive_clock(target, pulse)

    assert clock == pulse * len(target)


@pytest.mark.xfail
def test_1():
    instr1 = Pattern([0]) * 8

    instr2 = (Pattern([True]) * 2 + Pattern([False]) * 2) * 2

    stacked = stack_instructions([with_name(instr1, "a"), with_name(instr2, "b")])
    assert stacked["b"] == instr2
