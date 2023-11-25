from typing import assert_never, overload, Literal, Optional

import polars

from core.session import ExperimentSession, Shot
from core.types import is_parameter, is_analog_value, is_quantity
from core.types.units import Unit
from .shot_data import DataImporter, LazyDataImporter

QuantityDType = polars.Struct(
    [
        polars.Field("magnitude", polars.Float64),
        polars.Field("units", polars.Categorical),
    ]
)


@overload
def get_parameters_importer(lazy: Literal[False]) -> DataImporter:
    ...


@overload
def get_parameters_importer(lazy: Literal[True]) -> LazyDataImporter:
    ...


def get_parameters_importer(lazy: bool = False) -> DataImporter | LazyDataImporter:
    """Returns a function that can be used to load the values of the parameters used for a shot.

    When the function returned is evaluated on a shot, it returns a polars dataframe with a single row and with several
    columns named after each parameter defined for the shot and containing their values.

    If some parameters are quantity with units, the dtype of the associated column will be `QuantityDType`, that
    contains two fields, magnitude and units.

    Args:
        lazy: if True, the importer returned itself returns polars.LazyFrame, otherwise it returns a polars.DataFrame.
    """

    def importer(shot: Shot, session: ExperimentSession):
        parameters = {
            str(parameter_name): value
            for parameter_name, value in shot.get_parameters(session).items()
        }

        series: list[polars.Series] = []

        for parameter_name, value in parameters.items():
            if is_parameter(value):
                if is_analog_value(value) and is_quantity(value):
                    magnitude = float(value.magnitude)
                    units = str(value.units)
                    s = polars.Series(
                        parameter_name, [(magnitude, units)], dtype=QuantityDType
                    )
                else:
                    s = polars.Series(parameter_name, [value])
            else:
                assert_never(value)
            series.append(s)
        series.sort(key=lambda s: s.name)
        dataframe = polars.DataFrame(series)
        if lazy:
            return dataframe.lazy()
        else:
            return dataframe

    return importer


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
