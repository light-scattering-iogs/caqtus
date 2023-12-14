from typing import Iterable

from core.configuration import Expression, VariableName
from core.configuration.sequence import StepName
from core.types import is_quantity
from core.types.units import units, convert_to_unit, get_magnitude
from .evaluation_error import ShotEvaluationError, DimensionalityError
from ..variable_namespace import VariableNamespace


def compile_step_durations(
    step_names: Iterable[StepName],
    step_durations: Iterable[Expression],
    variables: VariableNamespace,
) -> list[float]:
    """Evaluate a sequence of step durations into a list of step durations."""

    evaluated_durations = []
    for name, expression in zip(step_names, step_durations):
        try:
            duration = expression.evaluate(variables | units)
        except Exception as error:
            raise ShotEvaluationError(
                f"Couldn't evaluate duration of step '{name}' ({expression.body})"
            ) from error

        if not is_quantity(duration):
            raise ShotEvaluationError(
                f"Duration of step '{name}' ({expression.body}) is not a quantity"
            )

        try:
            seconds = convert_to_unit(duration, units[VariableName("s")])
        except Exception as error:
            raise DimensionalityError(
                f"Duration of step '{name} ({expression.body}) is not a duration (got"
                f" {duration})"
            ) from error
        evaluated_durations.append(float(get_magnitude(seconds)))
    return evaluated_durations
