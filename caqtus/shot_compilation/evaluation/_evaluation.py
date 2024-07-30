from collections.abc import Mapping, Callable, Iterable
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
    T
](evaluable: Evaluable[T], variables: Mapping[DottedVariableName, Any],) -> T: ...


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
    T, R1, R2
](
    evaluable: Evaluable[T],
    variables: Mapping[DottedVariableName, Any],
    transformer: tuple[Callable[[T], R1], Callable[[R1], R2]],
) -> R2: ...


@overload
def evaluate[
    T
](
    evaluable: Evaluable[T],
    variables: Mapping[DottedVariableName, Any],
    transformer: tuple[Callable, ...],
) -> Any: ...


def evaluate(evaluable, variables, transformer=None):
    """Evaluate the given evaluable object using the given variables.

    Args:
        evaluable: An object that can be evaluated to a value.
        variables: A mapping of variable names to values.
            The evaluable object will be interpreted given the values of these
            variables.
        transformer: Functions that transforms the evaluated value.
            For example, this can be used to convert the value to a specific unit or
            ensure that it is within a certain range.
            If None, the evaluated value is returned as is.
    """

    value = evaluable.evaluate(variables)

    if transformer is None:
        return value

    if callable(transformer):
        return transformer(value)

    if not isinstance(transformer, Iterable):
        raise TypeError(
            "The transformer must be a callable or an iterable of callables."
        )
    for t in transformer:
        value = t(value)

    return value
