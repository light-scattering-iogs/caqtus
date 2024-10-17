from __future__ import annotations

import abc
import functools
import math
from collections.abc import Iterable, Sequence
from typing import Optional, Mapping, Any

import attrs
import numpy as np

from caqtus.shot_compilation import ShotContext
from caqtus.shot_compilation.lane_compilation import DimensionedSeries
from caqtus.shot_compilation.timed_instructions import (
    TimedInstruction,
    Pattern,
    Concatenated,
    concatenate,
    Repeated,
    Ramp,
    create_ramp,
)
from caqtus.types.units import Unit, InvalidDimensionalityError, Quantity, dimensionless
from caqtus.types.variable_name import DottedVariableName
from caqtus.utils.itertools import pairwise
from .channel_output import ChannelOutput
from ..timing import TimeStep


class TimeIndependentMapping(ChannelOutput, abc.ABC):
    """A functional mapping of input values to output values independent of time.

    This represents channel transformations of the form:

    .. math::
        y(t) = f(x_0(t), x_1(t), ..., x_n(t))

    where x_0, x_1, ..., x_n are the input and y is the output.
    """

    @abc.abstractmethod
    def inputs(self) -> tuple[ChannelOutput, ...]:
        """Returns the input values of the mapping."""

        raise NotImplementedError

    def evaluate_max_advance_and_delay(
        self,
        time_step: TimeStep,
        variables: Mapping[DottedVariableName, Any],
    ) -> tuple[int, int]:
        advances_and_delays = [
            input_.evaluate_max_advance_and_delay(time_step, variables)
            for input_ in self.inputs()
        ]
        advances, delays = zip(*advances_and_delays, strict=True)
        return max(advances), max(delays)


def data_points_converter(data_points: Iterable[tuple[float, float]]):
    point_to_tuple = [(x, y) for x, y in data_points]
    return tuple(sorted(point_to_tuple))


@attrs.define
class CalibratedAnalogMapping(TimeIndependentMapping):
    """Maps its input to an output quantity by interpolating a set of points.

    This mapping is useful for example when one needs to convert an experimentally
    measurable quantity (e.g. the frequency sent to an AOM) as a function of a control
    parameter (e.g. the voltage sent to the AOM driver).
    In this example, we need to know which voltage to apply to the AOM driver to obtain
    a given frequency.
    This conversion is defined by a set of points (x, y) where x is the input quantity
    and y is the output quantity.
    In the example above, x would be the frequency and y would be the voltage, because
    for a given frequency, we need to know which voltage to apply to the AOM driver.

    Attributes:
        input_units: The units of the input quantity
        input_: Describe the input argument of the mapping.
        output_units: The units of the output quantity
        measured_data_points: tuple of (input, output) tuples.
        The points will be rearranged to have the inputs sorted.
    """

    input_: ChannelOutput = attrs.field(
        validator=attrs.validators.instance_of(ChannelOutput),
        on_setattr=attrs.setters.validate,
    )
    input_units: Optional[str] = attrs.field(
        converter=attrs.converters.optional(str),
        on_setattr=attrs.setters.convert,
    )
    output_units: Optional[str] = attrs.field(
        converter=attrs.converters.optional(str),
        on_setattr=attrs.setters.convert,
    )
    measured_data_points: tuple[tuple[float, float], ...] = attrs.field(
        converter=data_points_converter, on_setattr=attrs.setters.convert
    )

    @property
    def input_values(self) -> tuple[float, ...]:
        return tuple(x[0] for x in self.measured_data_points)

    @property
    def output_values(self) -> tuple[float, ...]:
        return tuple(x[1] for x in self.measured_data_points)

    def inputs(self) -> tuple[ChannelOutput]:
        return (self.input_,)

    def __getitem__(self, index: int) -> tuple[float, float]:
        return self.measured_data_points[index]

    def __setitem__(self, index: int, values: tuple[float, float]):
        new_data_points = list(self.measured_data_points)
        new_data_points[index] = values
        self.measured_data_points = tuple(new_data_points)

    def set_input(self, index: int, value: float):
        self[index] = (value, self[index][1])

    def set_output(self, index: int, value: float):
        self[index] = (self[index][0], value)

    def pop(self, index: int):
        """Remove a data point from the mapping."""

        new_data_points = list(self.measured_data_points)
        new_data_points.pop(index)
        self.measured_data_points = tuple(new_data_points)

    def insert(self, index: int, input_: float, output: float):
        """Insert a data point into the mapping."""

        new_data_points = list(self.measured_data_points)
        new_data_points.insert(index, (input_, output))
        self.measured_data_points = tuple(new_data_points)

    def evaluate(
        self,
        required_time_step: TimeStep,
        prepend: int,
        append: int,
        shot_context: ShotContext,
    ) -> DimensionedSeries[np.float64]:
        input_values = self.input_.evaluate(
            required_time_step,
            prepend,
            append,
            shot_context,
        )

        return apply_piecewise_linear_calibration(
            input_values,
            self.measured_data_points,
            Unit(self.input_units) if self.input_units is not None else dimensionless,
            Unit(self.output_units) if self.output_units is not None else dimensionless,
        )


def apply_piecewise_linear_calibration(
    values: DimensionedSeries[np.floating],
    calibration_points: Sequence[tuple[float, float]],
    input_point_units: Unit,
    output_point_units: Unit,
) -> DimensionedSeries[np.float64]:
    """Apply a piecewise linear calibration to a sequencer instruction.

    Args:
        values: The instruction to apply the calibration to.
        calibration_points: A sequence of (input, output) tuples that define the
            points to interpolate between.
            The input must be expressed in input_point_units.
            The output must be expressed in output_point_units.
            The points will be sorted by input value before applying the interpolation.
        input_point_units: The units of the input points of the calibration.
        output_point_units: The units of the output points of the calibration.

    Returns:
        A new series of values where each point is obtained by linearly interpolating
        between calibration points.
        This new series of values is expressed in base units corresponding to
        output_point_units.

    Raises:
        InvalidDimensionalityError: If the units of the input points of the calibration
            are not compatible with the units of the values to map.
    """

    input_points = Quantity(
        [x for x, _ in calibration_points], input_point_units
    ).to_base_units()
    output_points = Quantity(
        [y for _, y in calibration_points], output_point_units
    ).to_base_units()

    if input_points.units != values.units:
        raise InvalidDimensionalityError(
            f"Can't apply calibration with units {input_points.units} to "
            f"instruction with units {values.units}"
        )

    calibration = DimensionlessCalibration(
        list(zip(input_points.magnitude, output_points.magnitude, strict=True))
    )
    return DimensionedSeries(
        calibration.apply(values.values.as_type(np.dtype(np.float64))),
        output_points.units,
    )


class DimensionlessCalibration:
    def __init__(self, calibration_points: Sequence[tuple[float, float]]):
        if len(calibration_points) < 2:
            raise ValueError("Calibration must have at least 2 data points")
        input_points = [x for x, _ in calibration_points]
        output_points = [y for _, y in calibration_points]
        sorted_points = sorted(
            zip(input_points, output_points, strict=True), key=lambda x: x[0]
        )
        sorted_input_points = [x for x, _ in sorted_points]
        sorted_output_points = [y for _, y in sorted_points]
        # We add new flat segments before and after the calibration points to ensure
        # that the calibration is defined for all input values.
        self._input_points = np.array([-np.inf] + sorted_input_points + [+np.inf])
        assert np.all(np.diff(self._input_points) >= 0)
        self._output_points = np.array(
            [sorted_output_points[0]]
            + sorted_output_points
            + [sorted_output_points[-1]]
        )

    @property
    def input_points(self):
        return self._input_points[1:-1]

    @property
    def output_points(self):
        return self._output_points[1:-1]

    def __repr__(self):
        points = ", ".join(
            f"({x}, {y})"
            for x, y in zip(self.input_points, self.output_points, strict=True)
        )
        return f"Calibration({points})"

    def apply(
        self, instruction: TimedInstruction[np.float64]
    ) -> TimedInstruction[np.float64]:
        # We raise errors in pathological cases when the calibration is not
        # well-defined.
        with np.errstate(
            # Avoids ambiguous situation with 2 points at the same x coordinate, because
            # we don't know what to output for a vertical line.
            divide="raise",
            # Avoid situations with 2 x points very close that cause and infinite slope.
            over="raise",
            # Avoids situations with 2 x points are equal and 2 y points are equal,
            # which cause a 0/0 division.
            invalid="raise",
        ):
            np.diff(self._output_points) / np.diff(
                self._input_points
            )  # pyright: ignore[reportUnusedExpression]
        return self._apply_without_checks(instruction)

    @functools.singledispatchmethod
    def _apply_without_checks(
        self, instruction: TimedInstruction[np.float64]
    ) -> TimedInstruction[np.float64]:
        raise NotImplementedError(
            f"Don't know how to apply calibration to instruction of type "
            f"{type(instruction)}"
        )

    @_apply_without_checks.register
    def _apply_calibration_pattern(self, pattern: Pattern) -> Pattern[np.float64]:
        result = self._apply_explicit(pattern.array)
        return Pattern.create_without_copy(result)

    def _apply_explicit(self, value):
        result = np.interp(
            x=value,
            xp=self._input_points,
            fp=self._output_points,
        )
        return result

    @_apply_without_checks.register
    def _apply_calibration_concatenation(
        self, concatenation: Concatenated
    ) -> TimedInstruction[np.float64]:
        return concatenate(
            *(
                self._apply_without_checks(instruction)
                for instruction in concatenation.instructions
            )
        )

    @_apply_without_checks.register
    def _apply_calibration_repetition(
        self, repetition: Repeated
    ) -> TimedInstruction[np.float64]:
        return repetition.repetitions * self._apply_without_checks(
            repetition.instruction
        )

    @_apply_without_checks.register
    def _apply_calibration_ramp(self, r: Ramp) -> TimedInstruction[np.float64]:
        # Ramp maps t -> x(t) = a + (b - a) * t / length
        # Calibration maps x -> y in a piecewise linear way
        # We want to map t -> y(t)
        length = len(r)
        a = r.start
        b = r.stop

        if a == b:
            return Pattern([self._apply_explicit(a)]) * length

        def map_x_segment_to_t(x_0, x_1) -> tuple[float, float]:
            if b > a:
                return length * (x_0 - a) / (b - a), length * (x_1 - a) / (b - a)
            else:
                return length * (x_1 - a) / (b - a), length * (x_0 - a) / (b - a)

        # Find the segments in time over which the output y(t) is linear.
        time_segments = []
        for x0, x1 in pairwise(self._input_points):
            time_segments.append(map_x_segment_to_t(x0, x1))

        if b < a:
            time_segments.reverse()

        sections = []
        for lower, higher in time_segments:
            lower = min(max(lower, 0), length)
            higher = min(max(higher, 0), length)
            i_min = math.ceil(lower)
            i_max = math.ceil(higher)
            sections.append((i_min, i_max))

        sub_ramps = []
        for i_min, i_max in sections:
            if i_max == i_min:
                continue
            in_0 = evaluate_ramp(r, i_min)
            y_0 = self._apply_explicit(in_0)
            if i_max == i_min + 1:
                sub_ramps.append(Pattern([y_0]))
            else:
                in_1 = evaluate_ramp(r, i_max - 1)
                y_1 = self._apply_explicit(in_1)
                length = i_max - i_min
                sub_ramp = create_ramp(
                    y_0, y_0 + length * (y_1 - y_0) / (length - 1), i_max - i_min
                )
                sub_ramps.append(sub_ramp)
        return concatenate(*sub_ramps)


def evaluate_ramp(r: Ramp, t) -> float:
    return r.start + (r.stop - r.start) * t / len(r)
