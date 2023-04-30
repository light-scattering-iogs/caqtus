import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm

Parameters = tuple[float]
Values = np.ndarray


def log_likelihood(values, model, parameters) -> float:
    return float(np.sum(np.log(model(values, *parameters))))


def maximize_likelihood(
    values: Values, model, initial_parameters: Parameters, method: str = "Nelder-Mead", bounds=None
) -> Parameters:
    return minimize(
        lambda parameters: -log_likelihood(values, model, parameters),
        x0=np.array(initial_parameters),
        method=method,
        bounds=bounds,
    ).x


