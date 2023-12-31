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

    if not is_analog_value(value):
        raise ValueError(f"{value} is not an analog value")
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


def magnitude_in_unit(value: Quantity, unit: Optional[Unit | str]) -> Real:
    """Return the magnitude of a value in the given unit."""

    if not is_analog_value(value):
        raise ValueError(f"{value} is not an analog value")

    if not unit or Unit(unit).is_compatible_with(dimensionless):
        if not is_quantity(value):
            return value
        elif value.units.is_compatible_with(dimensionless):
            return value.to(unit).magnitude
        raise ValueError(f"Trying to get magnitude of value {value} in unit {unit!r}")
    else:
        if is_quantity(value):
            return value.to(unit).magnitude
        raise ValueError(f"Value {value} has no unit but unit {unit!r} was given")


def add_unit(magnitude: Real, unit: Optional[Unit]) -> AnalogValue:
    """Add a unit to a magnitude."""

    if unit is None:
        return magnitude
    return Quantity(magnitude, unit)
