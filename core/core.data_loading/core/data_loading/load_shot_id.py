import polars

from core.session import ExperimentSession, Shot
from .shot_data import ShotData


def load_shot_id(shot: Shot, session: ExperimentSession) -> ShotData:
    return polars.DataFrame(
        [
            polars.Series("sequence", [str(shot.sequence)], dtype=polars.Categorical),
            polars.Series("shot name", [shot.name], dtype=polars.Categorical),
            polars.Series("shot index", [shot.index], dtype=polars.Int64),
        ]
    )
