from __future__ import annotations

import importlib.resources
from collections.abc import Sequence
from typing import overload, Self

import pint._typing
import pint.facets
import pint.facets.nonmultiplicative.objects
import pint.facets.numpy.quantity
import pint.facets.numpy.unit
from pint.facets.plain.quantity import ScalarT

from caqtus.types.recoverable_exceptions import InvalidValueError

UnitLike = pint._typing.UnitLike


class Quantity[M: pint._typing.Magnitude](
    pint.facets.system.objects.SystemQuantity[M],
    pint.facets.numpy.quantity.NumpyQuantity[M],
    pint.facets.nonmultiplicative.objects.NonMultiplicativeQuantity[M],
    pint.facets.plain.PlainQuantity[M],
):

    @overload
    def __new__(
        cls, value: int | float, units: UnitLike | None = None
    ) -> Quantity[float]: ...

    @overload
    def __new__(cls, value: str, units: UnitLike | None = None) -> Self: ...

    @overload
    def __new__(  # type: ignore[misc]
        cls, value: Sequence[ScalarT], units: UnitLike | None = None
    ) -> Self: ...

    @overload
    def __new__(cls, value: Self, units: UnitLike | None = None) -> Self: ...

    def __new__(cls, value, units=None):
        if isinstance(value, int):
            return super().__new__(  # pyright: ignore[reportCallIssue]
                cls,
                float(value),  # pyright: ignore[reportArgumentType]
                units,
            )
        return super().__new__(cls, value, units)

    @property
    def units(self) -> Unit:
        u = super().units
        assert isinstance(u, Unit)
        return u

    def to_base_units(self) -> Quantity[M]:
        result = super().to_base_units()
        assert isinstance(result, Quantity)
        return result


class Unit(
    pint.facets.SystemRegistry.Unit,
    pint.facets.numpy.unit.NumpyUnit,
    pint.facets.nonmultiplicative.objects.NonMultiplicativeUnit,
    pint.facets.plain.PlainUnit,
):
    pass


class UnitRegistry(pint.UnitRegistry):
    Quantity = Quantity  # pyright: ignore[reportAssignmentType]
    Unit = Unit  # pyright: ignore[reportAssignmentType]


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
dimensionless = Quantity(1, "").units

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
