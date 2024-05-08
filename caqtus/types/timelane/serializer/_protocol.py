import abc
from typing import Protocol

from caqtus.utils.serialization import JSON
from ..timelane import TimeLane


class TimeLaneSerializerProtocol(Protocol):
    @abc.abstractmethod
    def dump(self, lane: TimeLane) -> JSON: ...

    @abc.abstractmethod
    def load(self, data: JSON) -> TimeLane: ...
