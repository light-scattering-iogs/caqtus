import importlib.resources

import pint

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
