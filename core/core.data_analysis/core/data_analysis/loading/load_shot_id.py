import polars
from core.session import ExperimentSession, Shot

from .combinable_importers import CombinableLoader


class LoadShotId(CombinableLoader):
    """Loads the id of a shot.

    When it is evaluated on a shot, it returns a polars dataframe with a single row and three
    columns: `sequence`, `shot name` and `shot index` that allows to identify the shot.
    """

    def __call__(self, shot: Shot, session: ExperimentSession):
        dataframe = polars.DataFrame(
            [
                polars.Series(
                    "sequence", [str(shot.sequence)], dtype=polars.Categorical
                ),
                polars.Series("shot index", [shot.index], dtype=polars.Int64),
            ]
        )
        return dataframe
