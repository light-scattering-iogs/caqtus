from __future__ import annotations

from collections.abc import Mapping, Iterable
from typing import Any, Optional, overload

import attrs
import numpy as np

from caqtus.types._array import FloatArray1D
from caqtus.types.units import (
    Unit,
    Quantity,
    dimensionless,
    is_scalar_quantity,
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
        evaluated = evaluate(self.input_, variables)
        if isinstance(evaluated, Quantity):
            input_value = evaluated
        else:
            input_value = Quantity(float(evaluated), dimensionless)
        result = interpolate(
            input_value,
            Quantity(
                [point[0] for point in self.measured_data_points],
                (
                    Unit(self.input_points_unit)
                    if self.input_points_unit
                    else dimensionless
                ),
            ),
            Quantity(
                [point[1] for point in self.measured_data_points],
                (
                    Unit(self.output_points_unit)
                    if self.output_points_unit
                    else dimensionless
                ),
            ),
        )
        return result.to_base_units()


@overload
def interpolate[
    InputUnits: Unit, OutputUnits: Unit, L: int
](
    values: Quantity[float, InputUnits],
    input_values: Quantity[FloatArray1D[L], InputUnits],
    output_values: Quantity[FloatArray1D[L], OutputUnits],
) -> Quantity[float, OutputUnits]: ...


@overload
def interpolate[
    InputUnits: Unit, OutputUnits: Unit, L: int
](
    values: Quantity[FloatArray1D, InputUnits],
    input_values: Quantity[FloatArray1D[L], InputUnits],
    output_values: Quantity[FloatArray1D[L], OutputUnits],
) -> Quantity[FloatArray1D, OutputUnits]: ...


def interpolate[
    InputUnits: Unit, OutputUnits: Unit, L: int
](
    values: Quantity[FloatArray1D | float, InputUnits],
    input_values: Quantity[FloatArray1D[L], InputUnits],
    output_values: Quantity[FloatArray1D[L], OutputUnits],
) -> Quantity[FloatArray1D | float, OutputUnits]:
    sorted_points = sorted(
        zip(input_values.magnitude, output_values.magnitude, strict=True),
        key=lambda x: x[0],
    )

    input_points = Quantity(
        [point[0] for point in sorted_points], input_values.units
    ).to_base_units()
    output_points = Quantity(
        [point[1] for point in sorted_points], output_values.units
    ).to_base_units()

    output_magnitude = np.interp(
        x=values.to_unit(input_values.units).magnitude,
        xp=input_points.magnitude,
        fp=output_points.magnitude,
    )
    if is_scalar_quantity(values):
        return Quantity(float(output_magnitude), output_points.units).to_unit(
            output_values.units
        )
    else:
        return Quantity[FloatArray1D](output_magnitude, output_points.units).to_unit(
            output_values.units
        )
