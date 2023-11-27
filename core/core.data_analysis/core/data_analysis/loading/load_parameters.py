from typing import assert_never, overload, Literal

import polars

from core.session import ExperimentSession, Shot
from core.types import is_parameter, is_analog_value, is_quantity
from .shot_data import DataImporter, LazyDataImporter


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
                    units = format(value.units, "~")
                    s = polars.Series(
                        parameter_name,
                        [
                            polars.Series("magnitude", [magnitude]),
                            polars.Series("units", [units], dtype=polars.Categorical),
                        ],
                        dtype=polars.Struct,
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
