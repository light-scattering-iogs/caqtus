"""This module defines the configuration used to compute the output of a sequencer
channel.

A channel can typically output a constant value, the values of a lane, a trigger for
another device, or a functional combination of these.

The union type `ChannelOutput` is used to represent the different possible outputs of a
channel.
Each possible type of output is represented by a different class.
An output class is a high-level description of what should be outputted by a channel.
The classes defined are only declarative and do not contain any logic to compute the
output.
For more information on how the output is evaluated, see
:mod:`core.compilation.sequencer_parameter_compiler`.
"""

from __future__ import annotations

import abc
from collections.abc import Iterable
from typing import TypeGuard, Optional

import attrs
import numpy as np

from caqtus.device.name import DeviceName
from caqtus.types.expression import Expression
from caqtus.utils import serialization


def validate_channel_output(instance, attribute, value):
    if not is_channel_output(value):
        raise TypeError(f"Output {value} is not of type ChannelOutput")


class TimeIndependentMapping(abc.ABC):
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


@attrs.define
class LaneValues:
    """Indicates that the output should be the values taken by a given lane.

    Attributes:
        lane: The name of the lane from which to take the values.
        default: The default value to take if the lane is absent from the shot
            time lanes.
    """

    lane: str = attrs.field(
        converter=str,
        on_setattr=attrs.setters.convert,
    )
    default: Optional[ChannelOutput] = attrs.field(
        default=None,
        validator=attrs.validators.optional(validate_channel_output),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self) -> str:
        if self.default is not None:
            return f"{self.lane} | {self.default}"
        return self.lane


def structure_lane_values(data, _):
    lane = data["lane"]
    default_data = data["default"]
    if isinstance(default_data, str):
        default_expression = serialization.structure(default_data, Expression)
        default = Constant(value=default_expression)
    else:
        default = serialization.structure(default_data, ChannelOutput)

    return LaneValues(lane=lane, default=default)


def unstructure_lane_values(lane_values):
    return {
        "lane": lane_values.lane,
        "default": serialization.unstructure(lane_values.default, ChannelOutput),
    }


@attrs.define
class DeviceTrigger:
    """Indicates that the output should be a trigger for a given device.

    Fields:
        device_name: The name of the device to generate a trigger for.
        default: If the device is not used in the sequence, fallback to this.
    """

    device_name: DeviceName = attrs.field(
        converter=lambda x: DeviceName(str(x)),
        on_setattr=attrs.setters.convert,
    )
    default: Optional[ChannelOutput] = attrs.field(
        default=None,
        validator=attrs.validators.optional(validate_channel_output),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self):
        return f"trig({self.device_name})"


def unstructure_device_trigger(device_trigger: DeviceTrigger):
    return {
        "device_name": device_trigger.device_name,
        "default": serialization.unstructure(device_trigger.default, ChannelOutput),
    }


@attrs.define
class Constant:
    """Indicates that the output should be held at a constant value during the shot."""

    value: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self):
        return str(self.value)


@attrs.define
class Advance:
    input_: ChannelOutput = attrs.field(
        validator=validate_channel_output,
        on_setattr=attrs.setters.validate,
    )
    advance: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self):
        return f"{self.input_} << {self.advance}"


@attrs.define
class Delay:
    input_: ChannelOutput = attrs.field(
        validator=validate_channel_output,
        on_setattr=attrs.setters.validate,
    )
    delay: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self):
        return f"{self.delay} >> {self.input_}"


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
        validator=validate_channel_output, on_setattr=attrs.setters.validate
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

    def interpolate(self, input_: np.ndarray) -> np.ndarray:
        """Interpolates the input to obtain the output.

        Args:
            input_: The input values to interpolate.
            It is assumed to be expressed in input_units.

        Returns:
            The interpolated output values, expressed in output_units.
            The values are linearly interpolated between the measured data points.
            If the input is outside the range of the measured data points, the output
            will be clipped to the range of the measured data points.
        """

        input_values = np.array(self.input_values)
        output_values = np.array(self.output_values)
        interp = np.interp(
            x=input_,
            xp=input_values,
            fp=output_values,
        )
        # Warning !!!
        # We want to make absolutely sure that the output is within the range of data
        # points that are measured, to avoid values that could be dangerous for the
        # hardware.
        # To ensure this, we clip the output to the range of the measured data points.
        min_ = np.min(output_values)
        max_ = np.max(output_values)
        clipped = np.clip(interp, min_, max_)
        return clipped

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

    def __str__(self):
        return f"{self.input_} [{self.input_units}] -> [{self.output_units}]"


ChannelOutput = (
    LaneValues | DeviceTrigger | Constant | Advance | Delay | CalibratedAnalogMapping
)

serialization.register_structure_hook(LaneValues, structure_lane_values)
serialization.register_unstructure_hook(LaneValues, unstructure_lane_values)

serialization.register_unstructure_hook(DeviceTrigger, unstructure_device_trigger)

serialization.configure_tagged_union(ChannelOutput, "type")


def is_channel_output(obj) -> TypeGuard[ChannelOutput]:
    return isinstance(
        obj,
        (LaneValues, DeviceTrigger, Constant, Advance, Delay, CalibratedAnalogMapping),
    )


# A channel output object is said to be a source if it generates values y(t) = f(t)
# an has no input value x(t).
ValueSource = LaneValues | DeviceTrigger | Constant


def is_value_source(obj) -> TypeGuard[ValueSource]:
    return isinstance(obj, (LaneValues, DeviceTrigger, Constant))
