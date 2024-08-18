import pytest

from caqtus.device.sequencer.instructions import (
    Pattern,
    with_name,
    create_ramp,
    merge_instructions,
)


def test():
    r = create_ramp(0, 1, 5)
    assert r[0] == 0
    assert r[1] == 0.2
    assert r[2] == 0.4
    assert r[3] == 0.6
    assert r[4] == 0.8
    with pytest.raises(IndexError):
        assert r[5] == 1


def test_0():
    r = create_ramp(0.0, 1.0, 5)
    pattern = Pattern([0.0]) * 5
    merged = merge_instructions(a=r, b=pattern)

    assert merged["a"] == r
    assert merged["b"] == create_ramp(0, 0, 5)


def test_1():
    r = create_ramp(0, 1, 5)
    pattern = Pattern([0.0]) * 5
    merged = merge_instructions(a=r, b=pattern)

    assert merged["a"] == r
    assert merged["b"] == create_ramp(0, 0, 5)


def test_2():
    r = with_name(create_ramp(0, 1, 5), "a")
    assert r[0:3]["a"] == create_ramp(0.0, 0.6, 3)


def test_3():
    r = create_ramp(0.0, 1.0, 5)
    pattern = Pattern([0.0]) * 3 + Pattern([1]) * 2

    merged = merge_instructions(a=r, b=pattern)

    assert merged["a"] == create_ramp(0.0, 0.6, 3) + create_ramp(0.6, 1.0, 2)
