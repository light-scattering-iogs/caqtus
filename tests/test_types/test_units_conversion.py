import math

import pytest

from caqtus.types.units import (
    DimensionalityError,
    Quantity,
    DECIBEL,
    MEGAHERTZ,
    dimensionless,
)


def test_0():
    assert Quantity(1, dimensionless).to_unit(DECIBEL).magnitude == 0


def test_1():
    assert Quantity(0, dimensionless).to_unit(DECIBEL).magnitude == -math.inf


def test_2():
    with pytest.raises(DimensionalityError):
        assert Quantity(10, MEGAHERTZ).to_unit(dimensionless)


def test_3():
    assert Quantity(10, MEGAHERTZ).magnitude == 10


def test_4():
    assert Quantity(10, dimensionless).magnitude == 10
