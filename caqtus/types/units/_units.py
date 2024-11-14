from __future__ import annotations

import importlib.resources
from collections.abc import Sequence
from typing import NewType, SupportsFloat
from typing import overload, Generic

import numpy as np
import pint._typing
import pint.facets
import pint.facets.nonmultiplicative.objects
import pint.facets.numpy.quantity
import pint.facets.numpy.unit
from typing_extensions import TypeIs, TypeVar

from caqtus.types.recoverable_exceptions import InvalidValueError
from .._array import FloatArray

UnitLike = pint._typing.UnitLike


class Unit(
    pint.facets.SystemRegistry.Unit,
    pint.facets.numpy.unit.NumpyUnit,
    pint.facets.nonmultiplicative.objects.NonMultiplicativeUnit,
    pint.facets.plain.PlainUnit,
):
    def to_base(self) -> BaseUnit:
        """Convert the unit to base units."""

        return BaseUnit(Quantity(1.0, self).to_base_units().units)

    def __pow__(self, power) -> Unit:
        result = super().__pow__(power)
        assert isinstance(result, Unit)
        return result


BaseUnit = NewType("BaseUnit", Unit)
"""A type that represents a unit expressed in base SI units."""


type Magnitude = float | FloatArray

M = TypeVar("M", bound=Magnitude, covariant=True, default=Magnitude)
U = TypeVar("U", bound=Unit, covariant=True, default=Unit)
V = TypeVar("V", bound=Unit, covariant=True, default=Unit)
A = TypeVar("A", bound=FloatArray, covariant=True, default=FloatArray)


class Quantity(
    pint.facets.system.objects.SystemQuantity[M],  # type: ignore[reportInvalidTypeArguments]
    pint.facets.numpy.quantity.NumpyQuantity[M],  # type: ignore[reportInvalidTypeArguments]
    pint.facets.nonmultiplicative.objects.NonMultiplicativeQuantity[M],  # type: ignore[reportInvalidTypeArguments]
    pint.facets.plain.PlainQuantity[M],  # type: ignore[reportInvalidTypeArguments]
    Generic[M, U],
):
    @overload
    def __new__(cls, value: int, units: V) -> Quantity[float, V]: ...

    @overload
    def __new__(cls, value: M, units: V) -> Quantity[M, V]: ...

    @overload
    def __new__(
        cls, value: Sequence[SupportsFloat], units: V
    ) -> Quantity[FloatArray, V]: ...

    def __new__(cls, value: int | Magnitude | Sequence[SupportsFloat], units: Unit):
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

    def to_unit(self, unit: V) -> Quantity[M, V]:
        """

        Raises:
            DimensionalityError: If the units are not compatible.
        """
        result = super().to(unit)
        assert isinstance(result, Quantity)
        return result

    @property
    def magnitude(self) -> M:
        mag = super().magnitude
        if isinstance(mag, np.ndarray):
            return mag.astype(float)  # type: ignore[reportReturnType]
        else:
            return float(mag)  # type: ignore[reportReturnType]


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
Dimensionless = NewType("Dimensionless", BaseUnit)
dimensionless = Dimensionless(BaseUnit(Unit("dimensionless")))

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

DIMENSIONLESS_UNITS = {"dB", "percent", "%"}

CURRENT_UNITS = {"A", "mA"}

VOLTAGE_UNITS = {"V", "mV"}

DISTANCE_UNITS = {"m", "mm", "µm", "um", "nm"}

ANGLE_UNITS = {"deg", "°", "rad"}

UNITS = (
    TIME_UNITS
    | FREQUENCY_UNITS
    | POWER_UNITS
    | DIMENSIONLESS_UNITS
    | CURRENT_UNITS
    | VOLTAGE_UNITS
    | DISTANCE_UNITS
    | ANGLE_UNITS
)


class InvalidDimensionalityError(InvalidValueError):
    """Raised when a value has an invalid dimensionality.

    This error is raised when a value has an invalid dimensionality and the user
    should fix it.
    """

    pass
