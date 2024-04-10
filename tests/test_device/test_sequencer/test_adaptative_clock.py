from caqtus.device.sequencer.compilation import get_adaptive_clock
from caqtus.device.sequencer.instructions import Pattern, stack_instructions, with_name


def test_0():
    target = Pattern([0, 1, 2, 3])

    pulse = Pattern([True]) * 10 + Pattern([False]) * 10

    clock = get_adaptive_clock(target, pulse)

    assert clock == pulse * len(target)


def test_1():
    instr1 = Pattern([0]) * 8

    instr2 = (Pattern([True]) * 2 + Pattern([False]) * 2) * 2

    a = with_name(instr1, "a")
    b = with_name(instr2, "b")

    stacked = stack_instructions([a, b])
    assert stacked["b"] == instr2


def test_2():
    instr1 = Pattern([0, 1]) * 3
    instr2 = Pattern([0, 1, 2]) * 2

    a = with_name(instr1, "a")
    b = with_name(instr2, "b")

    stacked = stack_instructions([a, b])
    assert stacked["a"] == Pattern([0, 1, 0, 1, 0, 1])
