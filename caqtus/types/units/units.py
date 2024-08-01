import importlib.resources
from numbers import Real
from typing import Optional, overload

import numpy as np
import pint._typing

from caqtus.types.recoverable_exceptions import InvalidValueError

units_definition_file = importlib.resources.files("caqtus.types.units").joinpath(
    "units_definition.txt"
)

ureg = pint.UnitRegistry(
    units_definition_file,
    autoconvert_offset_to_baseunit=True,
    cache_folder=":auto:",
)
unit_registry = ureg
pint.set_application_registry(unit_registry)
Quantity = pint.Quantity
Unit = pint.Unit
UnitLike = pint._typing.UnitLike
UndefinedUnitError = pint.UndefinedUnitError

DimensionalityError = pint.DimensionalityError
dimensionless = Quantity(1, "").units

TIME_UNITS = {"s", "ms", "µs", "us", "ns"}

FREQUENCY_UNITS = {
    "Hz",
    "kHz",
    "MHz",
    "GHz",
    "THz",
}

POWER_UNITS = {
    "W",
    "mW",
    "dBm",
}

DIMENSIONLESS_UNITS = {"dB"}

CURRENT_UNITS = {"A", "mA"}

VOLTAGE_UNITS = {"V", "mV"}

DISTANCE_UNITS = {"m", "mm", "µm", "um", "nm"}

DEGREE_UNITS = {"deg", "rad"}

UNITS = (
    TIME_UNITS
    | FREQUENCY_UNITS
    | POWER_UNITS
    | DIMENSIONLESS_UNITS
    | CURRENT_UNITS
    | VOLTAGE_UNITS
    | DISTANCE_UNITS
    | DEGREE_UNITS
)


class InvalidDimensionalityError(InvalidValueError):
    """Raised when a value has an invalid dimensionality.

    This error is raised when a value has an invalid dimensionality and the user
    should fix it.
    """

    pass


def is_in_base_units(units: Unit) -> bool:
    """Check if the units is only expressed in terms of base SI units.

    For example, `kg`, `m/s` are expressed in terms of base units, but `mg`, `km/h` or
    `dB` are not.

    Args:
        units: The units to check.

    Returns:
        True if the units are expressed in the base units of the registry.
    """

    return (1 * units).to_base_units().units == units


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
            assert is_in_base_units(base_units)
        return magnitude_in_base_units, base_units
