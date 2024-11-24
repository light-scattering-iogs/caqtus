from __future__ import annotations

from collections.abc import Mapping, Callable
from typing import SupportsFloat, Protocol

import numpy

from caqtus.types.recoverable_exceptions import InvalidTypeError
from caqtus.types.units import DimensionalityError
from caqtus.types.variable_name import VariableName
from ._scalar import Scalar

SCALAR_FUNCTIONS: Mapping[VariableName, ScalarFunction]


class InvalidArgumentCountError(InvalidTypeError):
    pass


class ScalarFunction(Protocol):
    """A function that operates on scalars."""

    def __call__(self, *args: Scalar) -> Scalar:
        """Call the function with the given arguments.

        The function must accept a variable number of arguments, even if the underlying
        function is only defined for a specific number of arguments.
        This is because the user can mess up and enter the wrong number of arguments,
        but the function must still handle the error gracefully and raise the correct
        exception.

        Raises:
            InvalidArgumentCountError: if the number of arguments passed to the function
                is not correct.
            RecoverableError: if the function cannot be evaluated due to the user's
                input.
        """

        ...


def float_to_scalar_function(
    function: Callable[[float], SupportsFloat]
) -> ScalarFunction:
    """Convert a function operating on a float to a function operating on scalars."""

    def wrapper(*args: Scalar):
        if len(args) != 1:
            raise InvalidArgumentCountError(
                f"{function.__name__}() can only be called with one argument, got "
                f"{len(args)}."
            )
        value = args[0]
        try:
            converted = float(value)
        except (ValueError, DimensionalityError):
            raise InvalidTypeError(
                f"{function.__name__}() expected a number, got {value!r}."
            ) from None
        return float(function(converted))

    return wrapper


SCALAR_FUNCTIONS = {
    VariableName("abs"): float_to_scalar_function(abs),
    VariableName("arccos"): float_to_scalar_function(numpy.arccos),
    VariableName("arcsin"): float_to_scalar_function(numpy.arcsin),
    VariableName("arctan"): float_to_scalar_function(numpy.arctan),
    VariableName("cos"): float_to_scalar_function(numpy.cos),
    VariableName("sin"): float_to_scalar_function(numpy.sin),
    VariableName("tan"): float_to_scalar_function(numpy.tan),
    VariableName("exp"): float_to_scalar_function(numpy.exp),
    VariableName("log"): float_to_scalar_function(numpy.log),
    VariableName("sqrt"): float_to_scalar_function(numpy.sqrt),
}
