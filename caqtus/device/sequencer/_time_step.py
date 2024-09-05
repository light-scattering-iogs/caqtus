import decimal

from typing import NewType

TimeStep = NewType("TimeStep", decimal.Decimal)
"""A type alias that represents the duration of a time step in nanoseconds.

A time step is represented as a decimal number to avoid floating point errors.
"""
