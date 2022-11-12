import logging
from abc import abstractmethod, ABC

import numpy
from pydantic import root_validator, Field

from settings_model import SettingsModel
from units import Quantity

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class AnalogUnitsMapping(SettingsModel, ABC):
    """Abstract class for a mapping between some input quantity to an output quantity"""

    @abstractmethod
    def convert(self, input_: Quantity) -> Quantity:
        ...

    @abstractmethod
    def get_input_units(self) -> str:
        ...

    @abstractmethod
    def get_output_units(self) -> str:
        ...


class CalibratedUnitsMapping(AnalogUnitsMapping):
    """Convert between input and output quantities by interpolating a set of measured points

    This mapping is for example useful when one needs to convert an experimentally measurable quantity (e.g. the
    transmission of an AOM) as a function of a control parameter (e.g. a modulation voltage). Note that in this case the
    measured quantity is the input and the control quantity is the output. This is because we will need to convert from
    the measured quantity to the control quantity which is what is actually outputted by a device.
    """

    input_units: str = ""
    output_units: str = ""
    input_values: tuple[float, ...] = Field(default_factory=tuple)
    output_values: tuple[float, ...] = Field(default_factory=tuple)

    @root_validator(pre=False)
    def order_input_values(cls, values):
        input_values = numpy.array(values.get("input_values"))
        output_values = numpy.array(values.get("output_values"))
        order = numpy.argsort(input_values)
        sorted_input_values = input_values[order]
        sorted_output_values = output_values[order]
        values["input_values"] = tuple(sorted_input_values)
        values["output_values"] = tuple(sorted_output_values)
        return values

    def get_input_units(self) -> str:
        return self.input_units

    def get_output_units(self) -> str:
        return self.output_units

    def convert(self, input_: Quantity) -> Quantity:
        input_values = numpy.array(self.input_values)
        output_values = numpy.array(self.output_values)
        interp = numpy.interp(
            x=input_.to(self.get_input_units()).magnitude,
            xp=input_values,
            fp=output_values,
        )
        min_ = numpy.min(output_values)
        max_ = numpy.max(output_values)
        clipped = numpy.clip(interp, min_, max_)
        return Quantity(clipped, units=self.get_output_units())
