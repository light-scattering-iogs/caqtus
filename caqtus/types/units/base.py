from numbers import Real
from typing import overload, Optional

import numpy as np

from ._units import Unit, Quantity, dimensionless


def base_units(units: Unit) -> Unit:
    """Return the base units of the given units.

    Args:
        units: The units to convert to base units.

    Returns:
        The base units of the given units.
    """

    return (
        Quantity(1.0, units).to_base_units().units
    )  # pyright: ignore[reportReturnType]


def is_in_base_units(units: Unit) -> bool:
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
def convert_to_base_units[
    T: (Real, np.ndarray)
](magnitude: T, units: None) -> tuple[T, None]: ...


@overload
def convert_to_base_units[
    T: (Real, np.ndarray)
](magnitude: T, units: Unit) -> tuple[np.ndarray, Optional[Unit]]: ...


def convert_to_base_units(magnitude, units):
    if units is None:
        return magnitude, None
    else:
        quantity = Quantity(magnitude, units)
        in_base_units = quantity.to_base_units()
        magnitude_in_base_units = in_base_units.magnitude
        base_units = in_base_units.units
        if base_units == dimensionless:
            base_units = None
        else:
            assert is_in_base_units(base_units)  # pyright: ignore[reportArgumentType]
        return magnitude_in_base_units, base_units
