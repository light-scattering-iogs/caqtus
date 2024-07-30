from collections.abc import Mapping, Callable
from typing import Protocol, Any, overload

from caqtus.types.variable_name import DottedVariableName


class Evaluable[T](Protocol):
    """Defines an object that can be evaluated to a value."""

    def evaluate(self, variables: Mapping[DottedVariableName, Any]) -> T:
        """Evaluate the object using the given variables.

        Args:
            variables: A mapping of variable names to values.
                The evaluable object will be interpreted given the values of these
                variables.

        Returns:
            The evaluated value.
        """

        raise NotImplementedError


@overload
def evaluate[
    T, R
](
    evaluable: Evaluable[T],
    variables: Mapping[DottedVariableName, Any],
    transformer: Callable[[T], R],
) -> R: ...


@overload
def evaluate[
    T
](
    evaluable: Evaluable[T],
    variables: Mapping[DottedVariableName, Any],
    transformer: None,
) -> T: ...


def evaluate(evaluable, variables, transformer=None):
    """Evaluate the given evaluable object using the given variables.

    Args:
        evaluable: An object that can be evaluated to a value.
        variables: A mapping of variable names to values.
            The evaluable object will be interpreted given the values of these
            variables.
        transformer: A function that transforms the evaluated value.
            For example, this can be used to convert the value to a specific unit or
            ensure that it is within a certain range.
            If None, the evaluated value is returned as is.
    """

    value = evaluable.evaluate(variables)

    if transformer is None:
        return value
    else:
        transformed = transformer(value)
        return transformed
