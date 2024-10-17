from typing import NewType

from ._units import Unit, BaseUnit

Second = NewType("Second", BaseUnit)
SECOND = Second(BaseUnit(Unit("s")))
NANOSECOND = Unit("ns")
MEGAHERTZ = Unit("MHz")

DECIBEL = Unit("dB")
