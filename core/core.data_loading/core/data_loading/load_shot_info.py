from typing import Literal, overload

import polars

from core.session import Shot, ExperimentSession
from .load_parameters import get_parameters_importer
from .load_shot_id import get_shot_id_importer
from .shot_data import DataImporter, LazyDataImporter


@overload
def get_shot_info_importer(lazy: Literal[False]) -> DataImporter:
    ...


@overload
def get_shot_info_importer(lazy: Literal[True]) -> LazyDataImporter:
    ...


def get_shot_info_importer(lazy: bool = False) -> DataImporter | LazyDataImporter:
    # We can't concatenate two LazyFrames horizontally, so we load them eagerly
    params_importer = get_parameters_importer(False)
    id_importer = get_shot_id_importer(False)

    def importer(shot: Shot, session: ExperimentSession):
        id_ = id_importer(shot, session)
        params = params_importer(shot, session)
        dataframe = polars.concat([id_, params], how="horizontal")
        if lazy:
            return dataframe.lazy()
        else:
            return dataframe

    return importer
