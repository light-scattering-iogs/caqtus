from collections.abc import Mapping

import numpy
import polars
import scipy.optimize

from .stats import is_error_dtype, VALUE_FIELD, ERROR_FIELD


def curve_fit(f, x_data, y_data, initial_values: Mapping[str, float]):
    x = numpy.array(x_data, dtype=numpy.float64)
    if is_error_dtype(y_data.dtype):
        y = numpy.array(y_data.struct.field("value"), dtype=numpy.float64)
        sigma = numpy.array(y_data.struct.field("error"), dtype=numpy.float64)
        if numpy.any(sigma == 0):
            raise ValueError("One of the error on y_data is 0")
    else:
        y = numpy.array(y_data, dtype=numpy.float64)
        sigma = None
    popt, pcov = scipy.optimize.curve_fit(
        f,
        x,
        y,
        p0=list(initial_values.values()),
        sigma=sigma,
        absolute_sigma=True,
        check_finite=True,
    )
    errors = numpy.sqrt(numpy.diag(pcov))
    return polars.DataFrame(
        [
            polars.Series(name, [{VALUE_FIELD: value, ERROR_FIELD: error}])
            for name, value, error in zip(initial_values, popt, errors)
        ]
    )
