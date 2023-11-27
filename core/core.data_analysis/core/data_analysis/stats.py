from collections.abc import Sequence
from typing import Optional, Literal, assert_never

import polars

from core.types.units import Unit
from .units import extract_unit, with_units_added_to_columns

VALUE_FIELD = "value"
ERROR_FIELD = "error"


def is_error_dtype(dtype: polars.DataType) -> bool:
    """Check if a dtype is a QuantityDType.

    Args:
        dtype: the dtype to check.

    Returns:
        True if the dtype is a polars.Struct with two fields, magnitude and units, False otherwise.
    """

    if isinstance(dtype, polars.Struct):
        if len(dtype.fields) == 2:
            if (
                dtype.fields[0].name == VALUE_FIELD
                and dtype.fields[1].name == ERROR_FIELD
            ):
                return True
    return False


def compute_stats_average(
    dataframe: polars.DataFrame,
    column_to_average: str,
    grouped_by: Sequence[str],
    error_type: Literal["sem", "std"] = "sem",
) -> polars.DataFrame:
    """Compute the nominal value and error of a column, grouped by hues.

    Here the nominal value is the mean of the column, and the error is either the standard error of the mean or the
    standard deviation.

    Args:
        dataframe: the dataframe containing the data to average.
        column_to_average: the name of the column to average.
        grouped_by: the names of the columns to use to group the data. Must have at least one element at the moment.
        error_type: the type of error to compute. Can be "sem" (standard error of the mean) or "std" (standard
            deviation). Defaults to "sem".

    Returns:
        A dataframe with the columns specified in hues, plus two columns named after the column to average, with the
        mean and standard error of the mean of the column to average.
    """

    if len(grouped_by) == 0:
        raise NotImplementedError("No hue specified")

    # We convert all the y values to a single unit, so that we can compute the mean and sem in a meaningful way.
    # Should add a way to select the unit to use for the averaging.
    y_magnitudes, y_unit = extract_unit(dataframe[column_to_average])

    # We need to convert all the grouped_by to a single unit, even if no operation is performed on them. The issue is
    # that two values can have different magnitude and unit, but still be equal. For example, 1 m and 100 cm are equal.
    # Converting to a single unit allows to avoid this problem.
    hues_magnitudes: dict[str, polars.Series] = {}
    hues_units: dict[str, Optional[Unit]] = {}

    for hue in grouped_by:
        hues_magnitudes[hue], hues_units[hue] = extract_unit(dataframe[hue])

    dataframe_without_units = polars.DataFrame(
        [*hues_magnitudes.values(), y_magnitudes]
    )

    value = polars.col(column_to_average).mean()
    if error_type == "sem":
        error = polars.col(column_to_average).std() / polars.Expr.sqrt(
            polars.col(column_to_average).count()
        )
    elif error_type == "std":
        error = polars.col(column_to_average).std()
    else:
        assert_never(error_type)
    dataframe_stats_without_units = (
        dataframe_without_units.lazy()
        .group_by(*grouped_by)
        .agg(
            polars.struct(value.alias(VALUE_FIELD), error.alias(ERROR_FIELD)).alias(
                column_to_average
            )
        )
        .sort(*grouped_by)
        .collect()
    )

    return with_units_added_to_columns(
        dataframe_stats_without_units, {**hues_units, column_to_average: y_unit}
    )
