import logging
from abc import abstractmethod
from datetime import datetime
from typing import Protocol, Any

from sequence.runtime import Shot
from sql_model import DataType

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ShotCollection(Protocol):
    @abstractmethod
    def get_shot_data(self, shot: Shot, data_type: DataType) -> dict[str, Any]:
        """Get the data of a given shot."""

        raise NotImplementedError()

    @abstractmethod
    def add_shot_data(
        self, shot: Shot, data: dict[str, Any], data_type: DataType
    ) -> None:
        """Add data to a given shot."""

        raise NotImplementedError()

    @abstractmethod
    def get_shot_start_time(self, shot: Shot) -> datetime:
        """Get the start time of a given shot."""

        raise NotImplementedError()

    @abstractmethod
    def get_shot_end_time(self, shot: Shot) -> datetime:
        """Get the end time of a given shot."""

        raise NotImplementedError()
