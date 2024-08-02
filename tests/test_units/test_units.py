import math

from hypothesis import given
from hypothesis.strategies import sampled_from, integers, lists, builds, none
from pint import OffsetUnitCalculusError

from caqtus.types.units import units, Unit

simple_unit = sampled_from(list(units.values()))


def power(unit: Unit, exponent: int) -> Unit:
    return unit**exponent


unit_with_exponent = builds(power, simple_unit, integers(min_value=-5, max_value=5))

multiple_units = lists(unit_with_exponent, min_size=1, max_size=10)


def valid_product(units: list[Unit]) -> bool:
    try:
        math.prod(units)
    except OffsetUnitCalculusError:
        return False
    return True


def product(units: list[Unit]) -> Unit:
    assert len(units) > 0
    result = units[0]
    for unit in units[1:]:
        result *= unit
    return result


@given(multiple_units)
def test_is_units(units):
    assert isinstance(product(units), Unit)


composite_unit = multiple_units.map(product)


@given(composite_unit)
def test_draw(units):
    assert isinstance(units, Unit)


optional_unit = none() | composite_unit
