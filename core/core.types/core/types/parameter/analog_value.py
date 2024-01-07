from numbers import Real
from typing import Any, Optional, TypeGuard

import numpy as np

from ..units import Quantity, Unit, DimensionalityError, dimensionless

AnalogValue = Real | Quantity


def is_analog_value(value: Any) -> TypeGuard[AnalogValue]:
    """Returns True if the value is an analog value, False otherwise."""

    return isinstance(value, (Real, Quantity))


def is_quantity(value: Any) -> TypeGuard[Quantity]:
    """Returns True if the value is a quantity, False otherwise."""

    return isinstance(value, Quantity)


def get_unit(value: AnalogValue) -> Optional[Unit]:
    """Returns the unit of the value if it has one, None otherwise."""

    if isinstance(value, Quantity):
        return value.units
    return None


def get_magnitude(value: Quantity) -> Real | np.ndarray:
    """Returns the magnitude of the value."""

    return value.magnitude


def convert_to_unit(value: Quantity, unit: Unit | str) -> Quantity:
    """Convert a value to the given unit."""

    try:
        return value.to(unit)
    except DimensionalityError as error:
        raise ValueError(
            f"Cannot convert {value} to unit {unit} because of dimensionality"
        ) from error


def magnitude_in_unit(value: AnalogValue, unit: Optional[Unit]) -> Real:
    """Return the magnitude of a value in the given unit."""

    if is_quantity(value):
        if unit is None:
            raise ValueError(f"Cannot convert quantity {value} to dimensionless")
        return value.to(unit).magnitude
    else:
        if unit is not None:
            raise ValueError(f"Cannot convert value {value} to unit {unit}")
        return value


def add_unit(magnitude: Real, unit: Optional[Unit]) -> AnalogValue:
    """Add a unit to a magnitude."""

    if unit is None:
        return magnitude
    return Quantity(magnitude, unit)


def are_units_compatible(unit1: Optional[Unit], unit2: Optional[Unit]) -> bool:
    """Return True if the two units are compatible, False otherwise."""

    if unit1 is None:
        return unit2 is None
    if unit2 is None:
        return unit1 is None

    return unit1.is_compatible_with(unit2)
