from __future__ import annotations

import abc
from collections.abc import Mapping
from typing import Any, TypeAlias, Union

import attrs

import caqtus.formatter as fmt
from caqtus.types.expression import Expression
from caqtus.types.parameter import (
    Parameter,
    is_parameter,
    is_quantity,
)
from caqtus.types.recoverable_exceptions import InvalidTypeError
from caqtus.types.variable_name import DottedVariableName


@attrs.define
class Transformation(abc.ABC):
    """Defines a transformation that can be applied to produce an output value."""

    def evaluate(self, variables: Mapping[DottedVariableName, Any]) -> OutputValue:
        """Evaluates the transformation using the given variables."""

        raise NotImplementedError


OutputValue: TypeAlias = Parameter
"""A value that can be used to compute the output of a device."""

EvaluableOutput: TypeAlias = Union[Expression, Transformation]
"""Defines an operation that can be evaluated to an output value.

Evaluable object can be used in the :func:`evaluate` function.
"""


def evaluate(
    input_: EvaluableOutput, variables: Mapping[DottedVariableName, Any]
) -> OutputValue:
    """Evaluates the input and returns the result as a parameter."""

    evaluated = input_.evaluate(variables)

    if not is_parameter(evaluated):
        if isinstance(input_, Expression):
            raise InvalidTypeError(
                f"{fmt.expression(input_)} does not evaluate to a parameter, "
                f"got {fmt.type_(type(evaluated))}.",
            )
        # We only make the error recoverable if the user messed up the expression.
        # Otherwise, it is a bug because transformations should always return an output
        # value.
        raise TypeError(f"Expected {OutputValue}, got {type(evaluated)}.")

    if is_quantity(evaluated):
        # We convert to base units ASAP to avoid dealing with non-linear units like dB
        # and dBm.
        return evaluated.to_base_units()
    return evaluated


evaluable_output_validator = attrs.validators.instance_of((Expression, Transformation))
