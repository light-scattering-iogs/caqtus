from typing import Callable, ParamSpec

import numpy
from pandas import DataFrame, Series
from scipy.optimize import curve_fit

P = ParamSpec("Parameters")


def fit_to_data(
    data: DataFrame,
    function: Callable[[float, P], float],
    var_x: str,
    var_y: str,
    p0: dict[str, float],
    include_errors: bool = True,
) -> Series:
    x = data.groupby(var_x)[var_x].mean()
    y = data.groupby(var_x)[var_y].mean()
    y_err = data.groupby(var_x)[var_y].std()

    def fit_function(x, *args):
        return function(
            x, **{parameter: value for parameter, value in zip(p0.keys(), args)}
        )

    popt, pcov = curve_fit(
        fit_function,
        x,
        y,
        p0=list(p0.values()),
        sigma=y_err,
        absolute_sigma=True,
        check_finite=True,
    )
    optimal_values = {parameter: value for parameter, value in zip(p0.keys(), popt)}
    errors = {
        f"{parameter}_error": value
        for parameter, value in zip(p0.keys(), numpy.diag(pcov) ** 0.5)
    }

    if include_errors:
        return Series(optimal_values | errors)
    else:
        return Series(optimal_values)


