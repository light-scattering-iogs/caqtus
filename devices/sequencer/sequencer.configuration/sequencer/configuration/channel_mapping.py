from abc import abstractmethod
from typing import Generic, TypeVar

import numpy
from pydantic import validator

from settings_model import SettingsModel
from units import Quantity, UndefinedUnitError

InputType = TypeVar("InputType")
OutputType = TypeVar("OutputType")


class OutputMapping(Generic[InputType, OutputType]):
    @abstractmethod
    def convert(self, input_: InputType) -> OutputType:
        ...


class DigitalMapping(SettingsModel, OutputMapping[bool, bool]):
    invert: bool = False

    def convert(self, input_):
        if self.invert:
            return ~input_
        else:
            return input_


class AnalogMapping(OutputMapping[float, float]):
    """Abstract class for a mapping between some input quantity to an output quantity

    Warnings:
        The notion of input/output units might be confusing. It means that the convert
        method takes input argument in input units and outputs a quantity in output
        units.
    """

    @abstractmethod
    def convert(self, input_):
        ...

    @abstractmethod
    def get_input_units(self) -> str:
        ...

    @abstractmethod
    def get_output_units(self) -> str:
        ...

    def format_units(self) -> str:
        """Format the units of the mapping as a string"""
        input_units = self.get_input_units()
        if input_units == "":
            input_units = "[]"
        elif "/" in input_units:
            input_units = f"[{input_units}]"

        output_units = self.get_output_units()
        if output_units == "":
            output_units = "[]"
        elif "/" in output_units:
            output_units = f"[{output_units}]"

        return f"{input_units}/{output_units}"


class CalibratedAnalogMapping(SettingsModel, AnalogMapping):
    """Convert between input and output quantities by interpolating a set of measured points

    This mapping is for example useful when one needs to convert an experimentally measurable quantity (e.g. the
    transmission of an AOM) as a function of a control parameter (e.g. a modulation voltage). Note that in this case the
    measured quantity is the input and the control quantity is the output. This is because we will need to convert from
    the measured quantity to the control quantity which is what is actually outputted by a device.

    Fields:
        input_units: The units of the input quantity
        output_units: The units of the output quantity
        measured_data_points: tuple of (input, output) tuples. The points will be rearranged to have the inputs sorted.
    """

    input_units: str = ""
    output_units: str = ""
    measured_data_points: tuple[tuple[float, float], ...]

    @validator("input_units")
    def validate_input_units(cls, input_units):
        try:
            Quantity(1, units=input_units)
        except UndefinedUnitError:
            raise ValueError(f"Unknown input units: {input_units}")
        return input_units

    @validator("output_units")
    def validate_output_units(cls, output_units):
        try:
            Quantity(1, units=output_units)
        except UndefinedUnitError:
            raise ValueError(f"Unknown output units: {output_units}")
        return output_units

    @validator("measured_data_points")
    def sort_by_input(cls, measured_data_points):
        return sorted(measured_data_points)

    def __init__(self, input_units: str = "", output_units: str = "", **kwargs):
        if "measured_data_points" in kwargs:
            measured_data_points = kwargs.pop("measured_data_points")
        elif "input_values" in kwargs and "output_values" in kwargs:
            input_values = kwargs.pop("input_values")
            output_values = kwargs.pop("output_values")
            measured_data_points = tuple(zip(input_values, output_values))
        else:
            measured_data_points = tuple()

        super().__init__(
            input_units=input_units,
            output_units=output_units,
            measured_data_points=measured_data_points,
        )

    def get_input_units(self) -> str:
        return self.input_units

    def get_output_units(self) -> str:
        return self.output_units

    @property
    def input_values(self) -> tuple[float, ...]:
        return tuple(x[0] for x in self.measured_data_points)

    @property
    def output_values(self) -> tuple[float, ...]:
        return tuple(x[1] for x in self.measured_data_points)

    def convert(self, input_):
        input_values = numpy.array(self.input_values)
        output_values = numpy.array(self.output_values)
        interp = numpy.interp(
            x=input_,
            xp=input_values,
            fp=output_values,
        )
        min_ = numpy.min(output_values)
        max_ = numpy.max(output_values)
        clipped = numpy.clip(interp, min_, max_)
        return clipped

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
        """Remove a data point from the mapping"""

        new_data_points = list(self.measured_data_points)
        new_data_points.pop(index)
        self.measured_data_points = tuple(new_data_points)

    def insert(self, index: int, input_: float, output: float):
        """Insert a data point into the mapping"""

        new_data_points = list(self.measured_data_points)
        new_data_points.insert(index, (input_, output))
        self.measured_data_points = tuple(new_data_points)
