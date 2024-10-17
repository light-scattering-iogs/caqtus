from __future__ import annotations

import importlib.resources
from typing import overload, Any, TYPE_CHECKING, Generic

import numpy as np
import pint._typing
import pint.facets
import pint.facets.nonmultiplicative.objects
import pint.facets.numpy.quantity
import pint.facets.numpy.unit
from typing_extensions import TypeIs, TypeVar

from caqtus.types.recoverable_exceptions import InvalidValueError

if TYPE_CHECKING:
    from .base import BaseUnit

UnitLike = pint._typing.UnitLike


class Unit(
    pint.facets.SystemRegistry.Unit,
    pint.facets.numpy.unit.NumpyUnit,
    pint.facets.nonmultiplicative.objects.NonMultiplicativeUnit,
    pint.facets.plain.PlainUnit,
):
    pass


type FloatArray = np.ndarray[Any, np.dtype[np.floating]]
type Magnitude = float | FloatArray


M = TypeVar("M", bound=Magnitude, default=Magnitude)
U = TypeVar("U", bound=Unit, covariant=True, default=Unit)
V = TypeVar("V", bound=Unit, covariant=True, default=Unit)
A = TypeVar("A", bound=FloatArray, covariant=True, default=FloatArray)


class Quantity(
    pint.facets.system.objects.SystemQuantity[M],
    pint.facets.numpy.quantity.NumpyQuantity[M],
    pint.facets.nonmultiplicative.objects.NonMultiplicativeQuantity[M],
    pint.facets.plain.PlainQuantity[M],
    Generic[M, U],
):
    @overload
    def __new__(cls, value: int, units: V) -> Quantity[float, V]: ...

    @overload
    def __new__(cls, value: M, units: V) -> Quantity[M, V]: ...

    def __new__(cls, value: int | Magnitude, units: Unit):
        if isinstance(value, int):
            return super().__new__(
                cls,
                float(value),  # type: ignore[reportArgumentType]
                units,
            )
        return super().__new__(cls, value, units)  # type: ignore[reportArgumentType]

    @property
    def units(self) -> U:
        u = super().units
        return u  # type: ignore[reportReturnType]

    def to_base_units(self) -> Quantity[M, "BaseUnit"]:
        result = super().to_base_units()
        assert isinstance(result, Quantity)
        return result


def is_quantity(value) -> TypeIs[Quantity]:
    """Returns True if the value is a quantity, False otherwise."""

    return isinstance(value, Quantity)


def is_scalar_quantity(value) -> TypeIs[Quantity[float]]:
    """Returns True if the value is a scalar quantity, False otherwise."""

    return is_quantity(value) and isinstance(value.magnitude, float)


class UnitRegistry(pint.UnitRegistry):
    Quantity = Quantity  # type: ignore[reportAssignmentType]
    Unit = Unit  # type: ignore[reportAssignmentType]


units_definition_file = importlib.resources.files("caqtus.types.units").joinpath(
    "units_definition.txt"
)

ureg = UnitRegistry(
    str(units_definition_file),
    autoconvert_offset_to_baseunit=True,
    cache_folder=":auto:",
)
unit_registry = ureg
pint.set_application_registry(unit_registry)


UndefinedUnitError = pint.UndefinedUnitError

DimensionalityError = pint.DimensionalityError
dimensionless = Unit("dimensionless")

TIME_UNITS = {"s", "ms", "µs", "us", "ns"}

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

VOLTAGE_UNITS = {"V", "mV"}

DISTANCE_UNITS = {"m", "mm", "µm", "um", "nm"}

DEGREE_UNITS = {"deg", "rad"}

UNITS = (
    TIME_UNITS
    | FREQUENCY_UNITS
    | POWER_UNITS
    | DIMENSIONLESS_UNITS
    | CURRENT_UNITS
    | VOLTAGE_UNITS
    | DISTANCE_UNITS
    | DEGREE_UNITS
)


class InvalidDimensionalityError(InvalidValueError):
    """Raised when a value has an invalid dimensionality.

    This error is raised when a value has an invalid dimensionality and the user
    should fix it.
    """

    pass
