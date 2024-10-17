from typing import Any, Optional, overload, TypeAlias

import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypeIs

from ..recoverable_exceptions import InvalidTypeError
from ..units import Quantity, Unit, dimensionless, UnitLike
from ..units._units import FloatArray

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


def get_unit(value: AnalogValue) -> Optional[Unit]:
    """Returns the unit of the value if it has one, None otherwise."""

    if isinstance(value, Quantity):
        return value.units
    return None


@overload
def magnitude_in_unit[
    M: float | FloatArray
](value: Quantity[M], unit: Optional[UnitLike]) -> M: ...


@overload
def magnitude_in_unit(value: float, unit: Optional[UnitLike]) -> float: ...


@overload
def magnitude_in_unit[A: FloatArray](value: A, unit: Optional[UnitLike]) -> A: ...


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


@overload
def add_unit(magnitude: float, unit: None) -> float: ...


@overload
def add_unit(magnitude: NDArray[np.floating], unit: None) -> NDArray[np.floating]: ...


@overload
def add_unit(magnitude: float, unit: Unit) -> Quantity[float]: ...


@overload
def add_unit(
    magnitude: NDArray[np.floating], unit: Unit
) -> Quantity[NDArray[np.floating]]: ...


def add_unit(magnitude, unit):
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
