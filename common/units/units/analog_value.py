from numbers import Real
from typing import Any, Optional

from .units import Quantity, Unit

AnalogValue = Real | Quantity


def is_analog_value(value: Any) -> bool:
    """Returns True if the value is an analog value, False otherwise."""

    return isinstance(value, (Real, Quantity))


def get_unit(value: AnalogValue) -> Optional[Unit]:
    """Returns the unit of the value if it has one, None otherwise."""

    if not is_analog_value(value):
        raise ValueError(f"{value} is not an analog value")
    if isinstance(value, Quantity):
        return value.units
    return None


def magnitude_in_unit(value: AnalogValue, unit: Optional[Unit]) -> Real:
    """Return the magnitude of a value in the given unit."""

    if not is_analog_value(value):
        raise ValueError(f"{value} is not an analog value")

    if unit is None:
        if isinstance(value, Quantity):
            raise ValueError(f"Value {value} has a unit but no unit was given")
        return value
    else:
        if isinstance(value, Quantity):
            return value.to(unit).magnitude
        raise ValueError(f"Value {value} has no unit but unit {unit} was given")


def add_unit(magnitude: Real, unit: Optional[Unit]) -> AnalogValue:
    """Add a unit to a magnitude."""

    if unit is None:
        return magnitude
    return Quantity(magnitude, unit)
