"""Module to represent and work with a shot configuration

A shot configuration is made of a unique list of steps and a set of lanes. The steps are specified by their name and
duration. Each lane correspond to a time series of actions to do on the experiment."""

import logging
from typing import Optional, Type, Union

import yaml
from anytree import NodeMixin
from pydantic import validator

from expression import Expression
from settings_model import SettingsModel, YAMLSerializable
from .lane import TLane, Lane, AnalogLane, DigitalLane

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


LaneName = str


class LaneReference(YAMLSerializable, NodeMixin):
    def __init__(self, lane_name: LaneName, parent: Optional["LaneGroup"] = None):
        self._lane_name = LaneName(lane_name)
        self.parent = parent
        self.children = []

    @property
    def lane_name(self):
        return self._lane_name

    @classmethod
    def representer(cls, dumper: yaml.Dumper, obj: "LaneReference") -> yaml.Node:
        return dumper.represent_str(obj._lane_name)

    @classmethod
    def constructor(
        cls: Type["LaneReference"], loader: yaml.Loader, node: yaml.Node
    ) -> "LaneReference":
        return cls(lane_name=node.value)

    def __eq__(self, other):
        if not isinstance(other, LaneReference):
            return False
        return self._lane_name == other._lane_name

    @property
    def row(self):
        return self.parent.children.index(self)

    def __repr__(self):
        return f"{self.__class__.__name__}({self._lane_name})"


class LaneGroup(YAMLSerializable, NodeMixin):
    def __init__(
        self,
        name: str,
        parent: Optional["LaneGroup"] = None,
        children: Optional[list[Union["LaneGroup", LaneReference]]] = None,
    ):
        self._name = str(name)
        self.parent = parent
        self.children = children

    def __eq__(self, other):
        if not isinstance(other, LaneGroup):
            return False
        return self._name == other._name and self.children == other.children

    @classmethod
    def representer(cls, dumper: yaml.Dumper, lane_group: "LaneGroup") -> yaml.Node:
        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {
                "name": lane_group._name,
                "children": lane_group.children,
            },
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node) -> "LaneGroup":
        data = loader.construct_mapping(node, deep=True)
        name = str(data.pop("name"))
        children = data.pop("children")
        for index, child in enumerate(children):
            if isinstance(child, str):
                children[index] = LaneReference(child)
        return cls(name=name, children=children)

    @property
    def row(self):
        return self.parent.children.index(self)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value


class LaneGroupRoot(LaneGroup):
    def __init__(
        self, children: Optional[list[Union["LaneGroup", LaneReference]]] = None
    ):
        super().__init__("_root", children=children)

    def __eq__(self, other):
        if not isinstance(other, LaneGroupRoot):
            return False
        return self.children == other.children

    @classmethod
    def representer(cls, dumper: yaml.Dumper, lane_group: "LaneGroupRoot") -> yaml.Node:
        return dumper.represent_sequence(
            f"!{cls.__name__}",
            lane_group.children,
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node) -> "LaneGroupRoot":
        data = loader.construct_sequence(node, deep=True)
        for index, child in enumerate(data):
            if isinstance(child, str):
                data[index] = LaneReference(child)
        return cls(children=data)

    @property
    def row(self):
        return 0

    def insert_lane(self, index: int, name: str):
        new_children = list(self.children)
        new_children.insert(index, LaneReference(name))
        self.children = new_children


class ShotConfiguration(SettingsModel):
    step_names: list[str] = ["..."]
    step_durations: list[Expression] = [Expression("...")]
    lanes: list[Lane] = []
    lane_groups: LaneGroupRoot = None

    @validator("step_durations")
    def validate_step_durations(cls, durations, values):
        if len(durations) != len(values["step_names"]):
            raise ValueError("Length of step durations must match length of step names")
        return durations

    @validator("lanes")
    def validate_lanes(cls, lanes, values):
        names = set()
        for lane in lanes:
            if len(lane) != len(values["step_names"]):
                raise ValueError(
                    f"Length of lane '{lane.name}' does not match length of steps"
                )
            if lane.name in names:
                raise ValueError(f"Duplicate lane name '{lane.name}'")
            names.add(lane.name)
        return lanes

    @validator("lane_groups")
    def validate_lane_groups(cls, lane_groups, values):
        lanes = values["lanes"]
        if lane_groups is None:
            lane_groups = LaneGroupRoot(
                children=[LaneReference(lane.name) for lane in lanes]
            )

        lane_references = set()
        for lane_group in lane_groups.descendants:
            if isinstance(lane_group, LaneReference):
                lane_references.add(lane_group.lane_name)

        lane_names = set(lane.name for lane in lanes)
        if lane_references != lane_names:
            raise ValueError(
                f"Lane groups don't reference all lanes: {lane_references} !="
                f" {lane_names}"
            )

        return lane_groups

    def get_lane_names(self) -> list[str]:
        return [lane.name for lane in self.lanes]

    def find_lane(self, lane_name: str) -> Optional[Lane]:
        for lane in self.lanes:
            if lane.name == lane_name:
                return lane

    @property
    def analog_lanes(self) -> list[AnalogLane]:
        return [lane for lane in self.lanes if isinstance(lane, AnalogLane)]

    @property
    def digital_lanes(self) -> list[DigitalLane]:
        return [lane for lane in self.lanes if isinstance(lane, DigitalLane)]

    def get_lanes(self, lane_type: Type[TLane]) -> dict[str, TLane]:
        return {lane.name: lane for lane in self.lanes if isinstance(lane, lane_type)}
