from inspect import signature

import numpy
import pandas
from scipy.optimize import curve_fit


def fit_to_data(data: pandas.DataFrame, f, x: str, y: str, p0=None, include_errors: bool = False):
    group = data.groupby(x)
    mean = group[y].mean()
    xdata = mean.index.values
    ydata = mean.values
    sigma = group[y].sem().values
    if any(numpy.isnan(sigma)):
        sigma = None
    popt, pcov = curve_fit(
        f, xdata, ydata, p0, sigma, absolute_sigma=True, check_finite=True
    )
    parameters = list(signature(f).parameters)[1:]
    result = {parameter: value for parameter, value in zip(parameters, popt)}
    if include_errors:
        errors = numpy.sqrt(numpy.diag(pcov))
        result |= {f"{parameter}.error": error for parameter, error in zip(parameters, errors)}
    return result




