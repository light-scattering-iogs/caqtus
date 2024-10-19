from typing import NewType

from ._units import Unit, BaseUnit

Second = NewType("Second", BaseUnit)
SECOND = Second(Unit("s").to_base())
NANOSECOND = Unit("ns")

HERTZ = Unit("Hz")
MEGAHERTZ = Unit("MHz")

DECIBEL = Unit("dB")

VOLT = Unit("V")
