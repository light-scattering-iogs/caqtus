import warnings
from typing import Optional

import numpy
import pandas
from scipy.optimize import curve_fit
from util.inspect_function import get_parameters


def fit_to_data(
        data: pandas.DataFrame,
        f,
        x: str,
        y: str,
        p0=None,
        se: Optional[str] = None,
        include_errors: bool = False,
        raise_error: bool = True,
        **kwargs,
) -> dict[str, float]:
    """Fit a function to data.

    This function tries to fit a given functional form to data contained in a DataFrame.

    Args:
        data: The data to fit.
        f: The function to fit.
        x: The name of the column containing the independent variable.
        y: The name of the column containing the dependent variable.
        p0: The initial guess for the parameters.
        se: The name of the column containing the standard errors on the dependent variable. If this is None, the
        standard errors are computed from the statistical uncertainties on the data.
        include_errors: Whether to include the errors in the fit result or not.
        raise_error: Whether to raise an error if the fit fails or not. If this is False, the function returns a
        dictionary with values set to NaN.


    Returns:
        A dictionary containing the fit parameters and their values. The keys are the name of the arguments of the
        function `f`. If `include_errors` is True, the dictionary also contains the standard errors on the fit
        parameters as `<parameter>.error`.

    """

    group = data.groupby(x)
    mean = group[y].mean()
    xdata = mean.index.values
    ydata = mean.values
    if se is None:
        sigma = group[y].sem().values
    else:
        sigma = group[se].mean().values
    sigma[numpy.where(sigma == 0)] = numpy.mean(sigma)
    if any(numpy.isnan(sigma)):
        sigma = None
    try:
        # noinspection PyTupleAssignmentBalance
        popt, pcov = curve_fit(
            f, xdata, ydata, p0, sigma, absolute_sigma=True, check_finite=True, **kwargs,
        )

    except Exception as e:
        if raise_error:
            raise
        else:
            warnings.warn(f"Fit failed: {e}")
            estimated_parameters = {
                parameter: numpy.nan for parameter in get_parameters(f)
            }
            estimated_errors = {
                f"{parameter}.error": numpy.nan for parameter in get_parameters(f)
            }
    else:
        estimated_parameters = {
            parameter: value for parameter, value in zip(get_parameters(f), popt)
        }
        estimated_errors = {
            f"{parameter}.error": error
            for parameter, error in zip(get_parameters(f), numpy.sqrt(numpy.diag(pcov)))
        }

    if include_errors:
        return {**estimated_parameters, **estimated_errors}
    return estimated_parameters
