from typing import overload, Optional, Any, NewType

import numpy as np
from typing_extensions import TypeIs

from . import is_scalar_quantity
from ._units import Unit, Quantity, dimensionless, FloatArray

BaseUnit = NewType("BaseUnit", Unit)
ScalarBaseQuantity = NewType("ScalarBaseQuantity", Quantity[float])
ArrayBaseQuantity = NewType("ArrayBaseQuantity", Quantity[FloatArray])


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
def convert_to_base_units(magnitude: float, unit: None) -> tuple[float, None]: ...


@overload
def convert_to_base_units[
    A: np.ndarray[Any, np.dtype[np.floating]]
](magnitude: A, unit: None) -> tuple[A, None]: ...


@overload
def convert_to_base_units(
    magnitude: float, unit: Unit
) -> tuple[float, Optional[BaseUnit]]: ...


@overload
def convert_to_base_units[
    A: np.ndarray[Any, np.dtype[np.floating]]
](magnitude: A, unit: Unit) -> tuple[A, Optional[BaseUnit]]: ...


def convert_to_base_units(
    magnitude: float | np.ndarray[Any, np.dtype[np.floating]], unit: Optional[Unit]
):
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


def is_base_quantity(value: Quantity) -> TypeIs[ScalarBaseQuantity | ArrayBaseQuantity]:
    """Check if the given value is expressed in base units."""

    return is_in_base_units(value.units)


@overload
def to_base_units(quantity: Quantity[float]) -> ScalarBaseQuantity: ...


@overload
def to_base_units(quantity: Quantity[FloatArray]) -> ArrayBaseQuantity: ...


def to_base_units(quantity: Quantity) -> ScalarBaseQuantity | ArrayBaseQuantity:
    """Convert the given quantity to base units.

    Args:
        quantity: The quantity to convert.

    Returns:
        The quantity expressed in base units.
    """

    if is_scalar_quantity(quantity):
        return ScalarBaseQuantity(quantity.to_base_units())
    else:
        return ArrayBaseQuantity(quantity.to_base_units())
