from collections.abc import Callable
from typing import Optional, NewType, TypedDict

from caqtus.utils.serialization import (
    JSON,
    is_valid_json_dict,
    JsonDict,
    copy_converter,
)
from ._protocol import TimeLaneSerializerProtocol
from ..timelane import TimeLane, TimeLanes
from ...expression import Expression

Tag = NewType("Tag", str)


type LaneDumper[L: TimeLane] = Callable[[L], JsonDict]
"""A function that serializes a time lane to a JSON dictionary."""

type LaneLoader[L: TimeLane] = Callable[[JsonDict], L]
"""A function that constructs a time lane from a JSON dictionary."""

converter = copy_converter()


class TimeLaneSerializer(TimeLaneSerializerProtocol):
    def __init__(self):
        self.dumpers: dict[type, tuple[LaneDumper, Tag]] = {}
        self.loaders: dict[Tag, LaneLoader] = {}

    def register_time_lane[
        L: TimeLane
    ](
        self,
        lane_type: type[L],
        dumper: LaneDumper[L],
        loader: LaneLoader[L],
        type_tag: Optional[str] = None,
    ) -> None:
        if type_tag is None:
            tag = Tag(lane_type.__qualname__)
        else:
            tag = Tag(type_tag)
        self.dumpers[lane_type] = (dumper, tag)
        self.loaders[tag] = loader

    def dump(self, lane: TimeLane) -> JsonDict:
        dumper, tag = self.dumpers[type(lane)]
        content = dumper(lane)
        if "type" in content:
            raise ValueError("The content already has a type tag.")
        content["type"] = tag
        return content

    def load(self, data: JsonDict) -> TimeLane:
        tag = data["type"]
        if not isinstance(tag, str):
            raise ValueError("Invalid type tag.")
        else:
            tag = Tag(tag)
        try:
            loader = self.loaders[tag]
        except KeyError:
            error = ValueError(f"Don't know how to load lane stored with tag `{tag}`.")
            error.add_note(
                "Make sure that the corresponding lane extension is registered."
            )
            raise error from None
        return loader(data)

    def unstructure_time_lanes(self, time_lanes: TimeLanes) -> JsonDict:
        return dict(
            step_names=converter.unstructure(time_lanes.step_names, list[str]),
            step_durations=converter.unstructure(
                time_lanes.step_durations, list[Expression]
            ),
            lanes={
                lane: self.dump(time_lane)
                for lane, time_lane in time_lanes.lanes.items()
            },
        )

    def structure_time_lanes(self, content: JsonDict) -> TimeLanes:
        step_names = converter.structure(content["step_names"], list[str])
        step_durations = converter.structure(
            content["step_durations"], list[Expression]
        )
        lanes_content = content["lanes"]
        if not is_valid_json_dict(lanes_content):
            raise ValueError("Invalid lanes content.")
        lanes = {}
        for lane, lane_content in lanes_content.items():
            if not is_valid_json_dict(lane_content):
                raise ValueError(f"Invalid content for lane {lane}.")
            lanes[lane] = self.load(lane_content)

        return TimeLanes(
            step_names=step_names,
            step_durations=step_durations,
            lanes=lanes,
        )


class TimeLanesDump(TypedDict):
    step_names: list[str]
    step_durations: list[Expression]
    lanes: dict[str, JSON]


def default_dumper(lane) -> JSON:
    raise NotImplementedError(f"Unsupported type {type(lane)}")
