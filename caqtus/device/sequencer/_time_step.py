import decimal
from typing import TypeAlias

# TODO: replace with pep 695 type alias once cattrs 24.1 is released
TimeStep: TypeAlias = decimal.Decimal
"""A type alias that represents the type of a time step.

A time step is represented as a decimal number to avoid floating point errors.
"""
