"""This module defines a custom dtype for polars dataframes that can be used to represent quantities with units. This
dtype is called QuantityDType and is a struct with two fields: magnitude and units. This module also defines functions
to add or remove units from series.
"""

from typing import Optional

import polars

from core.types.units import Unit

QuantityDType = polars.Struct(
    [
        polars.Field("magnitude", polars.Float64),
        polars.Field("units", polars.Categorical),
    ]
)


def add_unit(series: polars.Series, unit: Optional[Unit]) -> polars.Series:
    """Add a unit to a series, if it is not None.

    Args:
        series: the series to which the unit should be added. It should be a numeric series that can be converted to a
            Float64 series.
        unit: the unit to add. If None, the series is returned unchanged.

    Returns:
        A new series with the unit added. If the unit is None, the series is returned unchanged and has the same dtype.
        If the unit is not None, the series is returned with dtype QuantityDType.
    """

    if unit is None:
        return series
    else:
        return polars.Series(
            series.name,
            [
                series,
                polars.Series((str(unit),) * len(series), dtype=polars.Categorical),
            ],
            dtype=QuantityDType,
        )


def convert_to_single_unit(
    series: polars.Series,
) -> tuple[polars.Series, Optional[Unit]]:
    """Break the series into a magnitude series and a unit.

    If the series has dtype QuantityDType, this will attempt to convert all magnitudes to a given unit. It will then
    return a series of magnitudes only and their unit. If the series is any other dtype, it will be returned unchanged.
    """

    if series.dtype == QuantityDType:
        all_units = series.struct.field("units").unique().to_list()
        if len(all_units) == 1:
            unit = Unit(all_units[0])
        else:
            raise NotImplementedError(
                f"Series {series.name} is expressed in several units: {all_units}"
            )
        magnitude = series.struct.field("magnitude").alias(series.name)
    else:
        unit = None
        magnitude = series
    return magnitude, unit
