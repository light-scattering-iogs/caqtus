import math

from caqtus.types.parameter import magnitude_in_unit


def test_0():
    assert magnitude_in_unit(1, "dB") == 0.0


def test_1():
    assert magnitude_in_unit(0.0, "dB") == -math.inf
