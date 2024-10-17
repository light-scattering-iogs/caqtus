from typing import overload, Optional, NewType

from typing_extensions import TypeIs

from ._units import (
    Unit,
    Quantity,
    dimensionless,
    Magnitude,
)

BaseUnit = NewType("BaseUnit", Unit)


def base_units(units: Unit) -> BaseUnit:
    """Return the base units of the given units.

    Args:
        units: The units to convert to base units.

    Returns:
        The base units of the given units.
    """

    return BaseUnit(Quantity(1.0, units).to_base_units().units)


def is_in_base_units(units: Unit) -> TypeIs[BaseUnit]:
    """Check if the units is only expressed in terms of base SI units.

    For example, `kg`, `m/s` are expressed in terms of base units, but `mg`, `km/h` or
    `dB` are not.

    Args:
        units: The units to check.

    Returns:
        True if the units are expressed in the base units of the registry.
    """

    return base_units(units) == units


@overload
def convert_to_base_units[M: Magnitude](magnitude: M, unit: None) -> tuple[M, None]: ...


@overload
def convert_to_base_units[
    M: Magnitude
](magnitude: M, unit: Unit) -> tuple[M, Optional[BaseUnit]]: ...


def convert_to_base_units(
    magnitude: Magnitude, unit: Optional[Unit]
) -> tuple[Magnitude, Optional[BaseUnit]]:
    """Convert values into base units.

    Args:
        magnitude: The value to convert.
            Can be a scalar or an array of values.
        unit: The unit in which the magnitude is expressed.

    Returns:
        The magnitude in base units and the base units.
    """

    if unit is None:
        return magnitude, None
    else:
        quantity = Quantity(magnitude, unit)
        in_base_units = quantity.to_base_units()
        magnitude_in_base_units = in_base_units.magnitude
        base_units = in_base_units.units
        if base_units == dimensionless:
            base_units = None
        else:
            assert is_in_base_units(base_units)
        return magnitude_in_base_units, base_units


def is_base_quantity[
    M: Magnitude
](value: Quantity[M, Unit]) -> TypeIs[Quantity[M, BaseUnit]]:
    """Check if the given value is expressed in base units."""

    return is_in_base_units(value.units)
