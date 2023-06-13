import numpy as np
from scipy.optimize import minimize

from inspect_function import get_parameters

Parameters = dict[str, float]
Values = np.ndarray


def log_likelihood(values, model, parameters) -> float:
    return float(np.sum(np.log(model(values, *parameters))))


def maximize_likelihood(
        values: Values,
        model,
        initial_parameters: Parameters,
        method: str,
        constraints=None,
) -> Parameters:
    optimal_parameters = minimize(
        lambda parameters: -log_likelihood(values, model, parameters),
        x0=np.array(initial_parameters),
        method=method,
        constraints=constraints,
    ).x
    parameter_names = get_parameters(model)
    return {
        parameter: value
        for parameter, value in zip(parameter_names, optimal_parameters)
    }
