"""This module defines a custom dtype for polars dataframes that can be used to
represent quantities with units. This
dtype is called QuantityDType and is a struct with two fields: magnitude and units.
This module also defines functions
to add or remove units from series.
"""

from typing import Optional, Mapping

import polars
from typing_extensions import deprecated

from caqtus.types.units import Unit, Quantity

MAGNITUDE_FIELD = "magnitude"
UNITS_FIELD = "units"


@polars.api.register_expr_namespace("quantity")
class QuantityExpressions:
    def __init__(self, expr: polars.Expr):
        self._expr = expr

    def magnitude(self) -> polars.Expr:
        return self._expr.struct.field(MAGNITUDE_FIELD).name.keep()

    @deprecated("Use expr.quantity.units() instead.")
    def unit(self) -> polars.Expr:
        return self.units()

    def units(self) -> polars.Expr:
        return self._expr.struct.field(UNITS_FIELD).name.keep()


@polars.api.register_series_namespace("quantity")
class QuantitySeries:
    def __init__(self, s: polars.Series):
        self._s = s

    def extract_unit(self) -> tuple[polars.Series, Optional[str]]:
        """Break the series into a magnitude series and a unit.

        If the series has a quantity data type, this will attempt to convert all
        magnitudes to a given unit. It will then
        return a series of magnitudes only and their unit. If the series is any other
        dtype, it will be returned unchanged.
        """

        series = self._s
        if is_quantity_dtype(series.dtype):
            all_units = series.struct.field(UNITS_FIELD).unique().to_list()
            if len(all_units) == 1:
                unit = Unit(all_units[0])
            else:
                raise NotImplementedError(
                    f"Series {series.name} is expressed in several units: {all_units}"
                )
            magnitude = series.struct.field(MAGNITUDE_FIELD).alias(series.name)
        else:
            unit = None
            magnitude = series
        if unit is None:
            return magnitude, None
        else:
            return magnitude, format(unit, "~")


@polars.api.register_dataframe_namespace("quantity")
class QuantityDataframe:
    def __init__(self, df: polars.DataFrame):
        self._df = df

    def extract_units(self) -> tuple[polars.DataFrame, Mapping[str, Optional[str]]]:
        """Break a dataframe potentially containing quantities into its magnitude and
        unit components."""

        dataframe = self._df

        column_units = {}
        columns_magnitudes = {}
        for column in dataframe.columns:
            magnitude, unit = extract_unit(dataframe[column])
            columns_magnitudes[column] = magnitude
            column_units[column] = unit
        return polars.DataFrame(columns_magnitudes), column_units


def is_quantity_dtype(dtype: polars.DataType) -> bool:
    """Check if a dtype is a QuantityDType.

    Args:
        dtype: the dtype to check.

    Returns:
        True if the dtype is a polars.Struct with two fields, magnitude and units,
        False otherwise.
    """

    if isinstance(dtype, polars.Struct):
        if len(dtype.fields) == 2:
            if (
                dtype.fields[0].name == MAGNITUDE_FIELD
                and dtype.fields[1].name == UNITS_FIELD
            ):
                return True
    return False


def add_unit(series: polars.Series, unit: Optional[Unit]) -> polars.Series:
    """Add a unit to a series, if it is not None.

    Args:
        series: the series to which the unit should be added.
        unit: the unit to add. If None, the series is returned unchanged.

    Returns:
        A new series with the unit added. If the unit is None, the series is returned
        unchanged and has the same dtype.
        If the unit is not None, the series is returned with a quantity dtype having
        the unit as a categorical and
        the magnitude with the same dtype as the original series.
    """

    if unit is None:
        return series
    else:
        return polars.Series(
            series.name,
            [
                series.alias(MAGNITUDE_FIELD),
                polars.Series(
                    UNITS_FIELD, (str(unit),) * len(series), dtype=polars.Categorical
                ),
            ],
            dtype=polars.Struct,
        )


@deprecated("Use series.quantity.extract_unit() instead.")
def extract_unit(
    series: polars.Series,
) -> tuple[polars.Series, Optional[Unit]]:
    return series.quantity.extract_unit()  # pyright: ignore[reportAttributeAccessIssue]


@deprecated("Use dataframe.quantity.extract_units() instead.")
def extract_units(
    dataframe: polars.DataFrame,
) -> tuple[polars.DataFrame, Mapping[str, Optional[str]]]:
    return (
        dataframe.quantity.extract_units()  # pyright: ignore[reportAttributeAccessIssue]
    )


def convert_to_unit(
    series: polars.Series, target_unit: Optional[Unit]
) -> polars.Series:
    """Convert a series to a given unit.

    Args:
        series: the series to convert. If it has a quantity dtype, target_unit must
        be not be None. If it has any other
            dtype, target_unit must be None.
        target_unit: the unit to convert to.

    Returns:
        A new series with the same name as the original series. If unit is None,
        the series is returned unchanged. If
        the series has a quantity dtype, the series is returned with the same dtype,
        but all magnitudes converted to
        the target unit.
    """

    if target_unit is None:
        if is_quantity_dtype(series.dtype):
            raise ValueError(
                f"Series {series.name} is expressed in unit {extract_unit(series)[1]} "
                f"and target_unit is None"
            )
        else:
            return series

    magnitudes, unit = extract_unit(series)
    if unit is None:
        raise ValueError(
            f"Series {series.name} has no unit and needs to be converted to "
            f"{target_unit:~}"
        )
    else:
        quantity = Quantity(magnitudes.to_numpy(), unit).to(target_unit)
        return add_unit(polars.Series(series.name, quantity.magnitude), target_unit)


def magnitude_in_unit(series: polars.Series, unit: Optional[Unit]) -> polars.Series:
    """Return the magnitude of a series in a given unit.

    Args:
        series: the series to convert. It should have dtype QuantityDType.
        unit: the unit to convert to. If None and the series has a not a quantity
        dtype, the series is returned
            unchanged.

    Raises:
        ValueError: if the series has a quantity dtype and unit is None.

    Returns:
        A new series with the same name as the original series, with dtype Float64
        and all magnitudes
        converted to the target unit.
    """

    if unit is None:
        if is_quantity_dtype(series.dtype):
            raise ValueError(
                f"Series {series.name} is expressed in unit {extract_unit(series)[1]} "
                f"and target_unit is None"
            )
        else:
            return series
    return (
        convert_to_unit(series, unit).struct.field(MAGNITUDE_FIELD).alias(series.name)
    )


def with_columns_expressed_in_units(
    dataframe: polars.DataFrame, column_units: Mapping[str, Optional[Unit]]
) -> polars.DataFrame:
    """Compute the magnitude of columns in a dataframe to given units.

    Args:
        dataframe: the dataframe to convert.
        column_units: a mapping from column names to units.

    Returns:
        A new dataframe with the same columns as the original dataframe, but with all
        columns containing the magnitude
        of the original columns in the requested units.
    """

    return dataframe.with_columns(
        **{
            column: magnitude_in_unit(dataframe[column], column_units[column])
            for column in column_units
        }
    )


def with_units_added_to_columns(
    dataframe: polars.DataFrame, column_units: Mapping[str, Optional[Unit]]
) -> polars.DataFrame:
    """Add units to columns in a dataframe.

    Args:
        dataframe: the dataframe to convert.
        column_units: a mapping from column names to units. If the unit is None,
        the column is returned unchanged.

    Returns:
        A new dataframe with the same columns as the original dataframe, but with all
        columns containing the magnitude
        of the original columns with the requested units.
    """

    return dataframe.with_columns(
        **{
            column: add_unit(dataframe[column], column_units[column])
            for column in column_units
        }
    )
