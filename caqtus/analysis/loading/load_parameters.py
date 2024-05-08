from typing import Literal

import attrs
import polars

from caqtus.session import Shot, Sequence
from caqtus.types.parameter import is_analog_value, is_quantity, Parameter
from caqtus.types.variable_name import DottedVariableName
from .combinable_importers import CombinableLoader
from .sequence_cache import cache_per_sequence


@attrs.define
class LoadShotParameters(CombinableLoader):
    """Loads the parameters of a shot.

    When it is evaluated on a shot, it returns a polars dataframe with a single row and
    with several columns named after each parameter requested.

    If some parameters are quantity with units, the dtype of the associated column will
    be a quantity dtype with two fields, magnitude and units.

    Attributes:
        which: the parameters to load from a shot.
        If it is "sequence", only the parameters defined at the sequence level are
        loaded.
        If it is "globals", only the values of the global parameters at the time the
        sequence was launched are loaded.
        Note that the values of the globals parameters will be constant for all shot
        of a given sequence, unless they
        are overwritten by the sequence iteration.
        If "all", both sequence specific and global parameters are loaded.
        If it is an iterable of strings, only the parameters with the given names are
        loaded.
    """

    which: Literal["sequence", "all"] = "all"

    def __attrs_post_init__(self):
        self._get_local_parameters = cache_per_sequence(get_local_parameters)

    @staticmethod
    def _parameters_to_dataframe(
        parameters: dict[DottedVariableName, Parameter]
    ) -> polars.DataFrame:
        series: list[polars.Series] = []

        for parameter_name, value in parameters.items():
            name = str(parameter_name)
            if is_analog_value(value) and is_quantity(value):
                magnitude = float(value.magnitude)
                units = format(value.units, "~")
                s = polars.Series(
                    name,
                    [
                        polars.Series("magnitude", [magnitude]),
                        polars.Series("units", [units], dtype=polars.Categorical),
                    ],
                    dtype=polars.Struct,
                )
            else:
                s = polars.Series(name, [value])
            series.append(s)
        series.sort(key=lambda s: s.name)
        dataframe = polars.DataFrame(series)
        return dataframe

    def load(self, shot: Shot) -> polars.DataFrame:
        parameters = shot.get_parameters()

        if self.which == "all":
            pass
        elif self.which == "sequence":
            local_parameters = self._get_local_parameters(shot.sequence)
            parameters = {name: parameters[name] for name in local_parameters}
        elif self.which == "globals":
            raise NotImplementedError
        else:
            raise NotImplementedError

        return self._parameters_to_dataframe(parameters)


def get_local_parameters(sequence: Sequence) -> set[DottedVariableName]:
    return sequence.get_local_parameters()
