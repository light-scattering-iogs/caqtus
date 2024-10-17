from __future__ import annotations

from collections.abc import Mapping, Iterable, Sequence
from typing import Any, Optional, overload, assert_type

import attrs
import numpy as np

import caqtus.formatter as fmt
from caqtus.types.parameter import (
    magnitude_in_unit,
    add_unit,
)
from caqtus.types.parameter._analog_value import ScalarAnalogValue, ArrayAnalogValue
from caqtus.types.recoverable_exceptions import NotDefinedUnitError
from caqtus.types.units import (
    Unit,
    Quantity,
    UnitLike,
    DimensionalityError,
    InvalidDimensionalityError,
    UndefinedUnitError,
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
            self.measured_data_points, self.input_points_unit, self.output_points_unit
        )
        try:
            return interpolator(input_value)
        except DimensionalityError as e:
            raise InvalidDimensionalityError("Invalid dimensionality") from e


def to_base_units(
    values: Sequence[float], required_unit: Optional[UnitLike]
) -> tuple[Sequence[float], Optional[Unit]]:

    if required_unit is None:
        return values, None
    try:
        unit = Unit(required_unit)
    except UndefinedUnitError:
        raise NotDefinedUnitError(f"Undefined {fmt.unit(required_unit)}.") from None
    base_unit = Quantity(1, unit).to_base_units().units
    return [
        Quantity(value, unit).to(base_unit).magnitude for value in values
    ], base_unit  # pyright: ignore[reportReturnType]


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

    @overload
    def __call__(self, input_value: ScalarAnalogValue) -> ScalarAnalogValue: ...

    @overload
    def __call__(self, input_value: ArrayAnalogValue) -> ArrayAnalogValue: ...

    def __call__(self, input_value):

        input_magnitudes = magnitude_in_unit(input_value, self.input_unit)

        output_magnitude = np.interp(
            x=input_magnitudes,
            xp=self.input_points,
            fp=self.output_points,
            left=self.output_points[0],
            right=self.output_points[-1],
        )
        if np.isscalar(output_magnitude):
            assert isinstance(output_magnitude, np.floating)
            return add_unit(float(output_magnitude), self.output_unit)
        else:
            assert_type(output_magnitude, np.ndarray[Any, np.dtype[np.float64]])
            return add_unit(output_magnitude, self.output_unit)
