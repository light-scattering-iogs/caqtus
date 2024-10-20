import abc
from typing import Protocol

from caqtus.utils.serialization import JsonDict
from ..timelane import TimeLane, TimeLanes


class TimeLaneSerializerProtocol(Protocol):
    """Defines how to (un)structure time lanes."""

    @abc.abstractmethod
    def dump(self, lane: TimeLane) -> JsonDict:
        """Serialize a single time lane to a JSON dictionary."""

        ...

    @abc.abstractmethod
    def load(self, data: JsonDict) -> TimeLane:
        """Construct a single time lane from a JSON dictionary."""

        ...

    @abc.abstractmethod
    def unstructure_time_lanes(self, time_lanes: TimeLanes) -> JsonDict: ...

    @abc.abstractmethod
    def structure_time_lanes(self, content: JsonDict) -> TimeLanes: ...
