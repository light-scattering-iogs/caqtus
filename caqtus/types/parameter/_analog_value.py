from typing import Any, TypeAlias

import numpy as np
from typing_extensions import TypeIs

from .._array import FloatArray
from ..recoverable_exceptions import InvalidTypeError
from ..units import Quantity

ScalarAnalogValue: TypeAlias = float | Quantity[float]
ArrayAnalogValue: TypeAlias = FloatArray | Quantity[FloatArray]
AnalogValue: TypeAlias = ScalarAnalogValue | ArrayAnalogValue


class NotAnalogValueError(InvalidTypeError):
    pass


class NotQuantityError(InvalidTypeError):
    pass


def is_scalar_analog_value(value: Any) -> TypeIs[ScalarAnalogValue]:
    """Returns True if the value is a scalar analog value, False otherwise."""

    if isinstance(value, float):
        return True

    if isinstance(value, Quantity):
        return isinstance(value.magnitude, float)

    return False


def is_array_analog_value(value: Any) -> TypeIs[ArrayAnalogValue]:
    """Returns True if the value is an array analog value, False otherwise."""

    if isinstance(value, np.ndarray):
        return issubclass(value.dtype.type, np.floating)

    if isinstance(value, Quantity):
        return isinstance(value.magnitude, np.ndarray) and issubclass(
            value.magnitude.dtype.type, np.floating
        )

    return False


def is_analog_value(value: Any) -> TypeIs[AnalogValue]:
    """Returns True if the value is an analog value, False otherwise."""

    return is_scalar_analog_value(value) or is_array_analog_value(value)


def is_quantity(value: Any) -> TypeIs[Quantity]:
    """Returns True if the value is a quantity, False otherwise."""

    return isinstance(value, Quantity)
