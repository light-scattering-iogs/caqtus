import math

import pytest

from caqtus.types.parameter import magnitude_in_unit
from caqtus.types.units import Unit, DimensionalityError


def test_0():
    assert magnitude_in_unit(1, "dB") == 0.0


def test_1():
    assert magnitude_in_unit(0.0, "dB") == -math.inf


def test_2():
    with pytest.raises(DimensionalityError):
        assert magnitude_in_unit(10 * Unit("MHz"), None)


def test_3():
    assert magnitude_in_unit(10 * Unit("MHz"), "MHz") == 10


def test_4():
    assert magnitude_in_unit(10, None) == 10
