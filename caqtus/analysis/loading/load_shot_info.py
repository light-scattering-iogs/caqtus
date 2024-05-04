import datetime

import polars

from caqtus.session import Shot
from .combinable_importers import CombinableLoader
from ...session.sequence._async_shot import AsyncShot


class LoadShotTime(CombinableLoader):
    """Loads the time of a shot.

    When it is evaluated on a shot, it returns a polars dataframe with a single row and
    two columns: `start time` and `end time` with dtype `polars.Datetime` indicates
    when the shot started and ended.
    """

    def load(self, shot: Shot):
        return self._shot_time_to_dataframe(shot.get_start_time(), shot.get_end_time())

    @staticmethod
    def _shot_time_to_dataframe(
        start_time: datetime.datetime, stop_time: datetime.datetime
    ) -> polars.DataFrame:
        dataframe = polars.DataFrame(
            [
                polars.Series("start time", [start_time], dtype=polars.Datetime),
                polars.Series("end time", [stop_time], dtype=polars.Datetime),
            ]
        )
        return dataframe

    async def async_load(self, shot: AsyncShot):
        start_time = await shot.get_start_time()
        stop_time = await shot.get_end_time()
        return self._shot_time_to_dataframe(start_time, stop_time)
