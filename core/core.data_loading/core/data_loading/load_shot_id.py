from typing import overload, Literal

import polars

from core.session import ExperimentSession, Shot
from .shot_data import DataImporter, LazyDataImporter


@overload
def get_shot_id_importer(lazy: Literal[False]) -> DataImporter:
    ...


@overload
def get_shot_id_importer(lazy: Literal[True]) -> LazyDataImporter:
    ...


def get_shot_id_importer(lazy: bool = False) -> DataImporter | LazyDataImporter:
    """Returns a function that can be used to load a unique identifier from a shot.

    When the function returned is evaluated on a shot, it returns a polars dataframe with a single row and three
    columns: `sequence`, `shot name` and `shot index` that allows to identify the shot.

    Args:
        lazy: if True, the importer returned itself returns polars.LazyFrame, otherwise it returns a polars.DataFrame.
    """

    def importer(shot: Shot, session: ExperimentSession):
        dataframe = polars.DataFrame(
            [
                polars.Series(
                    "sequence", [str(shot.sequence)], dtype=polars.Categorical
                ),
                polars.Series("shot name", [shot.name], dtype=polars.Categorical),
                polars.Series("shot index", [shot.index], dtype=polars.Int64),
            ]
        )
        if lazy:
            return dataframe.lazy()
        else:
            return dataframe

    return importer
