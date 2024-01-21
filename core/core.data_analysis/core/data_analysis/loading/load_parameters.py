import polars
from core.session import ExperimentSession, Shot
from core.types.parameter import is_analog_value, is_quantity

from .combinable_importers import CombinableLoader


class LoadShotParameters(CombinableLoader):
    """Loads the parameters of a shot.

    When it is evaluated on a shot, it returns a polars dataframe with a single row and
    with several columns named after each parameter defined for the shot and containing
    their values.

    If some parameters are quantity with units, the dtype of the associated column will
    be a quantity dtype with two fields, magnitude and units.
    """

    def __call__(self, shot: Shot, session: ExperimentSession) -> polars.DataFrame:
        parameters = {
            str(parameter_name): value
            for parameter_name, value in shot.get_parameters(session).items()
        }

        series: list[polars.Series] = []

        for parameter_name, value in parameters.items():
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
            series.append(s)
        series.sort(key=lambda s: s.name)
        dataframe = polars.DataFrame(series)
        return dataframe
