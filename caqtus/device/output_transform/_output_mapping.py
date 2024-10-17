from __future__ import annotations

from collections.abc import Mapping, Iterable, Sequence
from typing import Any, Optional

import attrs
import numpy as np

from caqtus.types.units import (
    DimensionalityError,
    InvalidDimensionalityError,
    Unit,
    Quantity,
    dimensionless,
)
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
        interpolator = Interpolator(
            self.measured_data_points,
            Unit(self.input_points_unit) if self.input_points_unit else dimensionless,
            Unit(self.output_points_unit) if self.output_points_unit else dimensionless,
        )
        try:
            return interpolator(input_value)
        except DimensionalityError as e:
            raise InvalidDimensionalityError("Invalid dimensionality") from e


class Interpolator:
    def __init__(
        self,
        measured_data_points: Sequence[tuple[float, float]],
        input_units: Unit,
        output_units: Unit,
    ):
        measured_data_points = sorted(measured_data_points, key=lambda x: x[0])
        self.input_points = Quantity(
            [point[0] for point in measured_data_points], input_units
        ).to_base_units()
        self.output_points = Quantity(
            [point[1] for point in measured_data_points], output_units
        ).to_base_units()

    def __call__(self, input_value: OutputValue) -> OutputValue:
        if not isinstance(input_value, Quantity):
            input_value = Quantity(input_value, dimensionless)

        output_magnitude = np.interp(
            x=input_value.to_unit(self.input_points.units).magnitude,
            xp=self.input_points.magnitude,
            fp=self.output_points.magnitude,
        )
        return Quantity(float(output_magnitude), self.output_points.units)
