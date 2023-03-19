import copy

from sequence.configuration import OptimizationVariableInfo
from sequence.runtime import Shot
from units import Quantity


class Optimizer:
    def __init__(
        self,
        optimization_variables: list[OptimizationVariableInfo],
        context_variables: dict,
    ):
        self._optimization_variables = optimization_variables
        self._context_variables = copy.deepcopy(context_variables)
        self._bounds = evaluate_optimization_bounds(
            self._optimization_variables, self._context_variables
        )

        self._initial_values = evaluate_initial_values(
            self._optimization_variables, self._context_variables
        )

        for variable_name, initial_value in self._initial_values.items():
            minimum, maximum = self._bounds[variable_name]
            if not (minimum <= initial_value <= maximum):
                raise ValueError(
                    f"Initial value {initial_value} for variable {variable_name} is not in the range [{minimum}, {maximum}]"
                )

    def suggest_values(self) -> dict[str]:
        return self._initial_values

    def register(self, values: dict[str], score: float):
        pass


def evaluate_optimization_bounds(
    optimization_variables: list[OptimizationVariableInfo],
    context_variables: dict,
) -> dict[str, tuple[Quantity, Quantity]]:
    bounds = {}
    for variable in optimization_variables:
        name = variable["name"]
        first_bound = variable["first_bound"].evaluate(context_variables)
        second_bound = variable["second_bound"].evaluate(context_variables)
        minimum = min(first_bound, second_bound)
        maximum = max(first_bound, second_bound)
        bounds[name] = (minimum, maximum)
    return bounds


def evaluate_initial_values(
    optimization_variables: list[OptimizationVariableInfo], context_variables: dict
) -> dict[str]:
    return {
        variable["name"]: variable["initial_value"].evaluate(context_variables)
        for variable in optimization_variables
    }


class Evaluator:
    def compute_score(self, shots: tuple[Shot, ...]) -> float:
        print(shots)
        return 0
