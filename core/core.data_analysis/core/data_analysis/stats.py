from collections.abc import Sequence
from typing import Optional

import polars

from core.types.units import Unit
from .units import convert_to_single_unit, add_unit


def compute_stats_average(
    dataframe: polars.DataFrame,
    column_to_average: str,
    hues: Sequence[str],
) -> polars.DataFrame:
    """Compute the mean and standard error of the mean of a column, grouped by hues.

    Args:
        dataframe: the dataframe containing the data to average.
        column_to_average: the name of the column to average.
        hues: the names of the columns to use to group the data. Must have at least one element at the moment.

    Returns:
        A dataframe with the columns specified in hues, plus two columns named after the column to average, with the
        mean and standard error of the mean of the column to average.
    """

    if len(hues) == 0:
        raise NotImplementedError("No hue specified")

    mean_column = f"{column_to_average}.mean"
    sem_column = f"{column_to_average}.sem"

    # We convert all the y values to a single unit, so that we can compute the mean and sem in a meaningful way.
    # Should add a way to select the unit to use for the averaging.
    y_magnitudes, y_unit = convert_to_single_unit(dataframe[column_to_average])

    # We need to convert all the hues to a single unit, even so no operation is performed on them. The issue is that
    # two values can have different magnitude and unit, but still be equal. For example, 1 m and 100 cm are equal.
    # Converting to a single unit allows to avoid this problem.
    hues_magnitudes: dict[str, polars.Series] = {}
    hues_units: dict[str, Optional[Unit]] = {}

    for hue in hues:
        hues_magnitudes[hue], hues_units[hue] = convert_to_single_unit(dataframe[hue])

    dataframe_without_units = polars.DataFrame(
        [*hues_magnitudes.values(), y_magnitudes]
    )

    mean = polars.col(column_to_average).mean()
    sem = polars.col(column_to_average).std() / polars.Expr.sqrt(
        polars.col(column_to_average).count()
    )
    dataframe_stats_without_units = (
        dataframe_without_units.lazy()
        .group_by(*hues)
        .agg(mean.alias(mean_column), sem.alias(sem_column))
        .sort(*hues)
        .collect()
    )

    columns = [
        (dataframe_stats_without_units[hue], hues_units[hue]) for hue in hues
    ] + [
        (dataframe_stats_without_units[mean_column], y_unit),
        (dataframe_stats_without_units[sem_column], y_unit),
    ]

    series_with_units = [add_unit(series, unit) for series, unit in columns]
    dataframe_stats = polars.DataFrame(series_with_units)

    return dataframe_stats
