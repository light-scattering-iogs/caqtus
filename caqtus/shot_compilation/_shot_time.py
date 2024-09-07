import decimal
from typing import NewType

Time = NewType("Time", decimal.Decimal)
"""A type for representing time in seconds.

It uses a decimal.Decimal to represent time in seconds to avoid floating point errors.
"""

ns = Time(decimal.Decimal("1e-9"))
