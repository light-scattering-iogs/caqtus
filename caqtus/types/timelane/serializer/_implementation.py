from collections.abc import Callable
from typing import TypeVar, Optional, NewType

from caqtus.utils import serialization
from caqtus.utils.serialization import JSON
from ._protocol import TimeLaneSerializerProtocol
from ..timelane import TimeLane, TimeLanes
from ...expression import Expression

L = TypeVar("L", bound=TimeLane)

Tag = NewType("Tag", str)
Dumper = Callable[[L], JSON]
Loader = Callable[[JSON], L]


class TimeLaneSerializer(TimeLaneSerializerProtocol):
    def __init__(self):
        self.dumpers: dict[type, tuple[Dumper, Tag]] = {}
        self.loaders: dict[Tag, Loader] = {}

    def register_time_lane(
        self,
        lane_type: type[L],
        dumper: Dumper[L],
        loader: Loader[L],
        type_tag: Optional[str] = None,
    ) -> None:
        if type_tag is None:
            tag = Tag(lane_type.__qualname__)
        else:
            tag = Tag(type_tag)
        self.dumpers[lane_type] = (dumper, tag)
        self.loaders[tag] = loader

    def dump(self, lane: TimeLane) -> JSON:
        dumper, tag = self.dumpers[type(lane)]
        content = dumper(lane)
        if "type" in content:
            raise ValueError("The content already has a type tag.")
        content["type"] = tag
        return content

    def load(self, data: JSON) -> TimeLane:
        tag = data["type"]
        loader = self.loaders[tag]
        return loader(data)

    def unstructure_time_lanes(self, time_lanes: TimeLanes) -> serialization.JSON:
        return dict(
            step_names=serialization.converters["json"].unstructure(
                time_lanes.step_names, list[str]
            ),
            step_durations=serialization.converters["json"].unstructure(
                time_lanes.step_durations, list[Expression]
            ),
            lanes={
                lane: self.dump(time_lane)
                for lane, time_lane in time_lanes.lanes.items()
            },
        )


def default_dumper(lane) -> JSON:
    raise NotImplementedError(f"Unsupported type {type(lane)}")
