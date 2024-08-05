import abc
from typing import Protocol

from caqtus.utils.serialization import JSON
from ..timelane import TimeLane, TimeLanes


class TimeLaneSerializerProtocol(Protocol):
    """Defines how to (un)structure time lanes."""

    @abc.abstractmethod
    def dump(self, lane: TimeLane) -> JSON: ...

    @abc.abstractmethod
    def load(self, data: JSON) -> TimeLane: ...

    @abc.abstractmethod
    def unstructure_time_lanes(self, time_lanes: TimeLanes) -> JSON: ...

