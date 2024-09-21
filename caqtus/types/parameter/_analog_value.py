from numbers import Real
from typing import Any, Optional, overload, TypeAlias

import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypeIs

from ..recoverable_exceptions import InvalidTypeError
from ..units import Quantity, Unit, dimensionless, UnitLike

AnalogValue: TypeAlias = float | NDArray[np.floating] | Quantity


class NotAnalogValueError(InvalidTypeError):
    pass


class NotQuantityError(InvalidTypeError):
    pass


def is_analog_value(value: Any) -> TypeIs[AnalogValue]:
    """Returns True if the value is an analog value, False otherwise."""

    if isinstance(value, np.ndarray):
        return issubclass(value.dtype.type, np.floating)
    elif isinstance(value, (float, Quantity)):
        return True
    return False


def is_quantity(value: Any) -> TypeIs[Quantity]:
    """Returns True if the value is a quantity, False otherwise."""

    return isinstance(value, Quantity)


def get_unit(value: AnalogValue) -> Optional[Unit]:
    """Returns the unit of the value if it has one, None otherwise."""

    if isinstance(value, Quantity):
        return value.units  # pyright: ignore[reportReturnType]
    return None


@overload
def magnitude_in_unit(
    value: Quantity, unit: Optional[UnitLike]
) -> Real | NDArray[np.floating]: ...


@overload
def magnitude_in_unit[R: Real](value: R, unit: Optional[UnitLike]) -> R: ...


@overload
def magnitude_in_unit[
    A: NDArray[np.floating]
](value: A, unit: Optional[UnitLike]) -> A: ...


def magnitude_in_unit(value, unit):
    """Return the magnitude of a value in the given unit."""

    if is_quantity(value):
        if unit is None:
            return value.to(dimensionless).magnitude
        return value.to(unit).magnitude
    else:
        if unit is None:
            return value
        else:
            value = value * dimensionless
            return value.to(unit).magnitude


def add_unit(
    magnitude: float | NDArray[np.floating], unit: Optional[Unit]
) -> AnalogValue:
    """Add a unit to a magnitude."""

    if unit is None:
        return magnitude
    return Quantity(magnitude, unit)  # pyright: ignore[reportReturnType]


def are_units_compatible(unit1: Optional[Unit], unit2: Optional[Unit]) -> bool:
    """Return True if the two units are compatible, False otherwise."""

    if unit1 is None:
        return unit2 is None
    if unit2 is None:
        return unit1 is None

    return unit1.is_compatible_with(unit2)
