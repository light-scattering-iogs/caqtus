__version__ = "0.1.0"

from pathlib import Path

import pint

ureg = pint.UnitRegistry(
    Path(__file__).parent / "units_definition.txt", autoconvert_offset_to_baseunit=True
)
Q = ureg.Quantity

TIME_UNITS = {"s", "ms", "µs", "ns"}

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

UNITS = TIME_UNITS | FREQUENCY_UNITS | POWER_UNITS | DIMENSIONLESS_UNITS | CURRENT_UNITS

units = {unit: getattr(ureg, unit) for unit in UNITS}
