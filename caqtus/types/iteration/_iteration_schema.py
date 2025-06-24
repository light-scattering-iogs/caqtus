"""Defines how a parameter can be iterated over in a sequence."""

import attrs

from caqtus.types.parameter import ParameterType, Parameter
from caqtus.types.units import Unit


@attrs.frozen
class Constant:
    """A constant value that can be used in parameter definitions."""

    value: Parameter


@attrs.frozen
class IteratedParameter:
    """A parameter that is iterated over in a sequence."""

    type_: ParameterType


@attrs.frozen
class DigitalUserTunableParameter:
    pass


@attrs.frozen
class AnalogUserTunableParameter:
    """A parameter that can be tuned by the user during sequence execution."""

    range_: tuple[float, float]
    unit: Unit


@attrs.frozen
class StepReference:
    step_index: int


@attrs.define
class ParameterInfo:
    definition: StepReference | None
    type_: (
        Constant
        | IteratedParameter
        | DigitalUserTunableParameter
        | AnalogUserTunableParameter
    )

