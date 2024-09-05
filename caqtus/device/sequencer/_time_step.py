import decimal

from typing import NewType

TimeStep = NewType("TimeStep", decimal.Decimal)
"""A type alias that represents the type of a time step.

A time step is represented as a decimal number to avoid floating point errors.
"""
