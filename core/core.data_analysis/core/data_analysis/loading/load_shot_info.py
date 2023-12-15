import polars
from core.session import Shot, ExperimentSession

from .combinable_importers import CombinableLoader


class LoadShotTime(CombinableLoader):
    """Loads the time of a shot.

    When it is evaluated on a shot, it returns a polars dataframe with a single row and two
    columns: `start time` and `end time` with dtype `polars.Datetime` indicates when the shot started and ended.
    """

    def __call__(self, shot: Shot, session: ExperimentSession):
        start_time = polars.Series(
            "start time", [shot.get_start_time(session)], dtype=polars.Datetime
        )
        stop_time = polars.Series(
            "end time", [shot.get_end_time(session)], dtype=polars.Datetime
        )
        return polars.DataFrame([start_time, stop_time])
