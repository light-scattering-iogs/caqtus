from typing import Protocol

from caqtus.utils.serialization import JSON
from ..timelane import TimeLane


class TimeLaneSerializerProtocol(Protocol):
    def dump(self, lane: TimeLane) -> JSON: ...

    def load(self, data: JSON) -> TimeLane: ...
