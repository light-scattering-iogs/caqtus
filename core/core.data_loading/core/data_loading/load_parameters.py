from typing import TypeAlias, assert_never

import polars

from core.session import ExperimentSession, Shot
from core.types import is_parameter, is_analog_value, is_quantity

ShotData: TypeAlias = polars.DataFrame
QuantityDType = polars.Struct(
    [
        polars.Field("magnitude", polars.Float64),
        polars.Field("units", polars.Categorical),
    ]
)


def load_parameters(shot: Shot, session: ExperimentSession) -> ShotData:
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
    return polars.DataFrame(series)
