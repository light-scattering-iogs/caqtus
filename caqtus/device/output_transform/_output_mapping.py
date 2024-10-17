from __future__ import annotations

from collections.abc import Mapping, Iterable
from typing import Any, Optional, assert_type

import attrs
import numpy as np

from caqtus.types.parameter import (
    magnitude_in_unit,
    add_unit,
)
from caqtus.types.units import (
    DimensionalityError,
    InvalidDimensionalityError,
    Unit,
)
from caqtus.types.units.base import convert_to_base_units
from caqtus.types.variable_name import DottedVariableName
from ._transformation import (
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

    Attributes:
        input_: An operation that can be evaluated to an output value.
            The transformation is applied to this value.
        measured_data_points: A list of measured data points as tuples of input and
            output values.
        input_points_unit: The unit of the input points.
            The result of the input evaluation will be converted to this unit.
        output_points_unit: The unit of the output points.
            The result of the transformation will be converted to this unit.
    """

    input_: EvaluableOutput = attrs.field(
        validator=evaluable_output_validator,
        on_setattr=attrs.setters.validate,
    )
    measured_data_points: tuple[tuple[float, float], ...] = attrs.field(
        converter=_data_points_converter, on_setattr=attrs.setters.convert
    )
    input_points_unit: Optional[str] = attrs.field(
        converter=attrs.converters.optional(str),
        on_setattr=attrs.setters.convert,
    )
    output_points_unit: Optional[str] = attrs.field(
        converter=attrs.converters.optional(str),
        on_setattr=attrs.setters.convert,
    )

    def evaluate(self, variables: Mapping[DottedVariableName, Any]) -> OutputValue:
        input_value = evaluate(self.input_, variables)
        input_units = Unit(self.input_points_unit) if self.input_points_unit else None
        output_units = (
            Unit(self.output_points_unit) if self.output_points_unit else None
        )
        interpolator = Interpolator(
            self.measured_data_points, input_units, output_units
        )
        try:
            return interpolator(input_value)
        except DimensionalityError as e:
            raise InvalidDimensionalityError("Invalid dimensionality") from e


class Interpolator:
    def __init__(
        self,
        measured_data_points: Iterable[tuple[float, float]],
        input_units: Optional[Unit],
        output_units: Optional[Unit],
    ):
        measured_data_points = sorted(measured_data_points, key=lambda x: x[0])
        self.input_points, self.input_unit = convert_to_base_units(
            np.array([point[0] for point in measured_data_points]), input_units
        )
        self.output_points, self.output_unit = convert_to_base_units(
            np.array([point[1] for point in measured_data_points]), output_units
        )

    def __call__(self, input_value: OutputValue) -> OutputValue:
        input_magnitude = magnitude_in_unit(input_value, self.input_unit)
        assert_type(input_magnitude, float)

        output_magnitude = np.interp(
            x=input_magnitude,
            xp=self.input_points,
            fp=self.output_points,
            left=self.output_points[0],
            right=self.output_points[-1],
        )
        return add_unit(float(output_magnitude), self.output_unit)
