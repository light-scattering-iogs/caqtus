import logging
from abc import abstractmethod
from datetime import datetime
from typing import Protocol, Any

from sequence.runtime import Shot

from experiment.session.data_type import DataType

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ShotCollection(Protocol):
    @abstractmethod
    def get_shot_data(self, shot: Shot, data_label: str) -> Any:
        """Get data stored for a given shot specified by their label.

        Args:
            shot: The shot to get data from.
            data_label: The label of the data to get.

        Returns:
            The data stored for the given shot and label.

        Raises:
            KeyError: If there is no data stored for the given shot and label.
        """

        raise NotImplementedError()

    @abstractmethod
    def get_all_shot_data(self, shot: Shot, data_type: DataType) -> dict[str, Any]:
        """Get all the data stored for a shot for a given data type."""

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
