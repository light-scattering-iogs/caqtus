from collections.abc import Sequence

from caqtus.types.expression import Expression
from caqtus.types.parameter import is_quantity, magnitude_in_unit
from caqtus.types.units.unit_namespace import units
from ..variable_namespace import VariableNamespace


def evaluate_step_durations(
    steps: Sequence[tuple[str, Expression]], variables: VariableNamespace
) -> list[float]:
    """Returns the durations of each step in seconds.

    Args:
        steps: A sequence of (name, duration) pairs.
        variables: The variables to use for evaluating duration expressions.

    Returns:
        A list of step durations in seconds.
    """

    result = []

    all_variables = variables.dict()

    for name, duration in steps:
        try:
            evaluated = duration.evaluate(all_variables)
        except Exception as e:
            raise ValueError(
                f"Couldn't evaluate duration <{duration}> of step <{name}>"
            ) from e

        if not is_quantity(evaluated):
            raise TypeError(
                f"Duration <{duration}> of step <{name}> is not a quantity "
                f"({evaluated})"
            )

        try:
            seconds = magnitude_in_unit(evaluated, "s")
        except Exception as error:
            raise ValueError(
                f"Duration <{duration}> of step <{name}> can't be converted to seconds "
                f"({evaluated})"
            ) from error
        if seconds < 0:
            raise ValueError(
                f"Duration <{duration}> of step <{name}> is negative ({seconds})"
            )
        result.append(seconds)
    return result
