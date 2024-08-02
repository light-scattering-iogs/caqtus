from __future__ import annotations

import abc
import functools
import math
from collections.abc import Iterable, Sequence
from typing import Optional, Mapping, Any

import attrs
import cattrs
import numpy as np

from caqtus.shot_compilation import ShotContext
from caqtus.types.units import Unit, convert_to_base_units, InvalidDimensionalityError
from caqtus.types.variable_name import DottedVariableName
from caqtus.utils import serialization
from caqtus.utils.itertools import pairwise
from ._structure_hook import structure_channel_output
from .channel_output import ChannelOutput, EvaluatedOutput
from ..instructions import (
    SequencerInstruction,
    Pattern,
    Concatenated,
    concatenate,
    Repeated,
    Ramp,
    ramp,
)


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
        time_step: int,
        variables: Mapping[DottedVariableName, Any],
    ) -> tuple[int, int]:
        advances_and_delays = [
            input_.evaluate_max_advance_and_delay(time_step, variables)
            for input_ in self.inputs()
        ]
        advances, delays = zip(*advances_and_delays)
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
        required_time_step: int,
        prepend: int,
        append: int,
        shot_context: ShotContext,
    ) -> EvaluatedOutput:
        input_values = self.input_.evaluate(
            required_time_step,
            prepend,
            append,
            shot_context,
        )
        calibration = PiecewiseLinearCalibration(
            self.measured_data_points, self.input_units, self.output_units
        )
        if input_values.units != calibration.input_units:
            raise InvalidDimensionalityError(
                f"Can't apply calibration with units {input_values.units} to "
                f"instruction with units {self.input_units}"
            )
        output_values = calibration.apply(input_values.values)
        return output_values


class PiecewiseLinearCalibration:
    """Represents a piecewise linear calibration from input to output space.

    Args:
        calibration_points: A sequence of (input, output) tuples that define the
            points to interpolate between.
            The input must be expressed in input_point_units.
            The output must be expressed in output_point_units.
            The points will be sorted by input value before applying the interpolation.
        input_point_units: The units of the input points.
        output_point_units: The units of the output points.
    """

    def __init__(
        self,
        calibration_points: Sequence[tuple[float, float]],
        input_point_units: Optional[Unit],
        output_point_units: Optional[Unit],
    ):
        input_points = np.array([x for x, _ in calibration_points], dtype=np.float64)
        output_points = np.array([y for _, y in calibration_points], dtype=np.float64)
        input_magnitudes, self.input_units = convert_to_base_units(
            input_points, input_point_units
        )
        output_magnitudes, self.output_units = convert_to_base_units(
            output_points, output_point_units
        )
        self._calibration = Calibration(list(zip(input_magnitudes, output_magnitudes)))

    # def __repr__(self):
    #     points = ", ".join(
    #         f"({x}, {y})" for x, y in zip(self.input_points, self.output_points)
    #     )
    #     return f"Calibration({points}, {self.input_units}, {self.output_units})"

    def apply(
        self, instruction: SequencerInstruction[np.floating], units: Optional[Unit]
    ) -> EvaluatedOutput:
        """Apply the calibration to a sequencer instruction.

        Args:
            instruction: The instruction to apply the calibration to.
            units: The units in which the instruction is expressed.

        Returns:
            A new instruction where each point is obtained by interpolating calibration
            points.

            If a value in the instruction is smaller than the smallest input point, the
            output will be the output of the smallest input point.

            If a value in the instruction is larger than the largest input point, the
            output will be the output of the largest input point.
        """

        if units != self.input_units:
            raise InvalidDimensionalityError(
                f"Can't apply calibration with units {units} to "
                f"instruction with units {self.input_units}"
            )

        return EvaluatedOutput(
            self._calibration.apply(instruction.as_type(np.float64)), self.output_units
        )


class Calibration:
    def __init__(self, calibration_points: Sequence[tuple[float, float]]):
        if len(calibration_points) < 2:
            raise ValueError("Calibration must have at least 2 data points")
        input_points = np.array([x for x, _ in calibration_points], dtype=np.float64)
        output_points = np.array([y for _, y in calibration_points], dtype=np.float64)
        sorted_points = sorted(zip(input_points, output_points), key=lambda x: x[0])
        self.input_points = np.array([x for x, _ in sorted_points])
        self.output_points = np.array([y for _, y in sorted_points])

    @functools.singledispatchmethod
    def apply(
        self, instruction: SequencerInstruction[np.float64]
    ) -> SequencerInstruction[np.float64]:
        raise NotImplementedError(
            f"Don't know how to apply calibration to instruction of type "
            f"{type(instruction)}"
        )

    @apply.register
    def _apply_calibration_pattern(self, pattern: Pattern) -> Pattern[np.float64]:
        result = self._apply_explicit(pattern.array)
        return Pattern.create_without_copy(result)

    def _apply_explicit(self, value):
        result = np.interp(
            x=value,
            xp=self.input_points,
            fp=self.output_points,
        )
        assert np.all(np.isfinite(result))
        assert np.all(result <= max(self.output_points))
        assert np.all(result >= min(self.output_points))
        return result

    @apply.register
    def _apply_calibration_concatenation(
        self, concatenation: Concatenated
    ) -> SequencerInstruction[np.float64]:
        return concatenate(
            *(self.apply(instruction) for instruction in concatenation.instructions)
        )

    @apply.register
    def _apply_calibration_repetition(
        self, repetition: Repeated
    ) -> SequencerInstruction[np.float64]:
        return repetition.repetitions * self.apply(repetition.instruction)

    @apply.register
    def _apply_calibration_ramp(self, r: Ramp) -> SequencerInstruction[np.float64]:
        l = len(r)
        a = r.start
        b = r.stop

        if a == b:
            return Pattern([self._apply_explicit(a)]) * l

        def compute_bounds(x, y) -> tuple[float, float]:
            if b > a:
                return l * (x - a) / (b - a), l * (y - a) / (b - a)
            else:
                return l * (y - a) / (b - a), l * (x - a) / (b - a)

        time_segments = []
        for x0, x1 in pairwise(self.input_points):
            time_segments.append(compute_bounds(x0, x1))

        if b < a:
            time_segments.reverse()

        sections = []
        for lower, higher in time_segments:
            lower = min(max(lower, 0), l)
            higher = min(max(higher, 0), l)
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
                sub_ramp = ramp(
                    y_0, y_0 + length * (y_1 - y_0) / (length - 1), i_max - i_min
                )
                sub_ramps.append(sub_ramp)
        return concatenate(*sub_ramps)


def evaluate_ramp(r: Ramp, t) -> float:
    return r.start + (r.stop - r.start) * t / len(r)


# Workaround for https://github.com/python-attrs/cattrs/issues/430
structure_hook = cattrs.gen.make_dict_structure_fn(
    CalibratedAnalogMapping,
    serialization.converters["json"],
    input_=cattrs.override(struct_hook=structure_channel_output),
)

serialization.register_structure_hook(CalibratedAnalogMapping, structure_hook)
