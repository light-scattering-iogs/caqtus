"""Defines steps that ask the user for input during sequence iteration."""

import attrs

from caqtus.types.expression import Expression
from caqtus.types.variable_name import DottedVariableName

type UserInputStep = AnalogUserInputStep | DigitalUserInputStep


@attrs.define
class AnalogUserInputStep:
    """Declares a step that asks the user for an analog input value.

    Attributes:
        parameter: The name of the parameter to ask the user.
        range_: Unevaluated range of the parameter.
            This contains the bounds of the interval that the parameter will be able to
            be chosen in during sequence execution.
            The values of the tuple might not be ordered.
    """

    __match_args__ = ("parameter", "range_")

    parameter: DottedVariableName
    range_: tuple[Expression, Expression]


@attrs.define
class DigitalUserInputStep:
    """Declares a step that asks the user for a digital input value.

    Attributes:
        parameter: The name of the parameter to ask the user.
    """

    __match_args__ = ("parameter",)

    parameter: DottedVariableName
