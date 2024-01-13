from typing import Any, Optional, TypeGuard

from ..units import Quantity, Unit, DimensionalityError

AnalogValue = float | Quantity


def is_analog_value(value: Any) -> TypeGuard[AnalogValue]:
    """Returns True if the value is an analog value, False otherwise."""

    return isinstance(value, (float, Quantity))


def is_quantity(value: Any) -> TypeGuard[Quantity]:
    """Returns True if the value is a quantity, False otherwise."""

    return isinstance(value, Quantity)


def get_unit(value: AnalogValue) -> Optional[Unit]:
    """Returns the unit of the value if it has one, None otherwise."""

    if isinstance(value, Quantity):
        return value.units
    return None


def magnitude_in_unit(value: AnalogValue, unit: Optional[Unit | str]) -> float:
    """Return the magnitude of a value in the given unit."""

    if is_quantity(value):
        if unit is None:
            raise ValueError(f"Cannot convert quantity {value} to dimensionless")
        return value.to(unit).magnitude
    else:
        if unit is not None:
            raise ValueError(f"Cannot convert value {value} to unit {unit}")
        return value


def add_unit(magnitude: float, unit: Optional[Unit]) -> AnalogValue:
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
