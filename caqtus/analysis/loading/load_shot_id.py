import polars

from caqtus.session import Shot, PureSequencePath
from .combinable_importers import CombinableLoader


class LoadShotId(CombinableLoader):
    """Loads the id of a shot.

    When it is evaluated on a shot, it returns a polars dataframe with a single row and
    two columns: `sequence` and `shot index` that allows to identify the shot.
    """

    def load(self, shot: Shot):
        return self._shot_id_to_dataframe(shot.sequence.path, shot.index)

    async def async_load(self, shot: Shot):
        return self._shot_id_to_dataframe(shot.sequence.path, shot.index)

    @staticmethod
    def _shot_id_to_dataframe(path: PureSequencePath, index: int) -> polars.DataFrame:
        dataframe = polars.DataFrame(
            [
                polars.Series(
                    "sequence", [str(path)], dtype=polars.Categorical
                ),
                polars.Series("shot index", [index], dtype=polars.Int64),
            ]
        )
        return dataframe
