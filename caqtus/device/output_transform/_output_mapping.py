from __future__ import annotations

from collections.abc import Mapping, Iterable, Sequence
from typing import Any, Optional

import attrs
import numpy as np

import caqtus.formatter as fmt
from caqtus.types.parameter import (
    magnitude_in_unit,
    add_unit,
    AnalogValue,
    is_analog_value,
)
from caqtus.types.recoverable_exceptions import InvalidTypeError, NotDefinedUnitError
from caqtus.types.units import Unit, Quantity
from caqtus.types.units.units import (
    UnitLike,
    DimensionalityError,
    InvalidDimensionalityError,
)
from caqtus.types.variable_name import DottedVariableName
from .transformation import (
    Transformation,
    EvaluableOutput,
    evaluable_output_validator,
    OutputValue,
    evaluate,
)


def _data_points_converter(data_points: Iterable[tuple[float, float]]):
    point_to_tuple = [(x, y) for x, y in data_points]
    return tuple(sorted(point_to_tuple))


@attrs.define
class LinearInterpolation(Transformation):
    """Transforms an input value by applying a piecewise linear interpolation.

    This transformation stores a set of measured data points and interpolates the
    output value based on the input value.
    """

    input_: EvaluableOutput = attrs.field(
        validator=evaluable_output_validator,
        on_setattr=attrs.setters.validate,
    )
    input_points_unit: Optional[str] = attrs.field(
        converter=attrs.converters.optional(str),
        on_setattr=attrs.setters.convert,
    )
    output_points_unit: Optional[str] = attrs.field(
        converter=attrs.converters.optional(str),
        on_setattr=attrs.setters.convert,
    )
    measured_data_points: tuple[tuple[float, float], ...] = attrs.field(
        converter=_data_points_converter, on_setattr=attrs.setters.convert
    )

    def evaluate(self, variables: Mapping[DottedVariableName, Any]) -> OutputValue:
        input_value = evaluate(self.input_, variables)
        if not is_analog_value(input_value):
            raise InvalidTypeError(
                f"Expected an analog value, got {fmt.type_(type(input_value))}."
            )
        interpolator = Interpolator(
            self.measured_data_points, self.input_points_unit, self.output_points_unit
        )
        try:
            return interpolator(input_value)
        except DimensionalityError as e:
            raise InvalidDimensionalityError(f"Invalid dimensionality") from e


def to_base_units(
    values: Sequence[float], required_unit: Optional[UnitLike]
) -> tuple[Sequence[float], Optional[Unit]]:

    if required_unit is None:
        return values, None
    try:
        unit = Unit(required_unit)
    except NotDefinedUnitError:
        raise NotDefinedUnitError(f"Undefined {fmt.unit(required_unit)}.")
    base_unit = Quantity(1, unit).to_base_units().units
    return [
        Quantity(value, unit).to(base_unit).magnitude for value in values
    ], base_unit


class Interpolator:
    def __init__(
        self,
        measured_data_points: Iterable[tuple[float, float]],
        input_units: Optional[UnitLike],
        output_units: Optional[UnitLike],
    ):
        measured_data_points = sorted(measured_data_points, key=lambda x: x[0])
        self.input_points, self.input_unit = to_base_units(
            [point[0] for point in measured_data_points], input_units
        )
        self.output_points, self.output_unit = to_base_units(
            [point[1] for point in measured_data_points], output_units
        )

    def __call__(self, input_value: AnalogValue) -> AnalogValue:

        input_value = magnitude_in_unit(input_value, self.input_unit)

        output_magnitude = np.interp(
            x=input_value,
            xp=self.input_points,
            fp=self.output_points,
            left=self.output_points[0],
            right=self.output_points[-1],
        )
        return add_unit(output_magnitude, self.output_unit)
