"""Module to represent and work with a shot configuration

A shot configuration is made of a unique list of steps and a set of lanes. The steps are specified by their name and
duration. Each lane correspond to a time series of actions to do on the experiment."""

import logging
from typing import Optional, Type

from expression import Expression
from pydantic import validator
from settings_model import SettingsModel, YAMLSerializable

from .lane import TLane, Lane, AnalogLane, DigitalLane

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ShotConfiguration(SettingsModel):
    step_names: list[str] = ["..."]
    step_durations: list[Expression] = [Expression("...")]
    lanes: list[Lane] = []

    @validator("step_durations")
    def validate_step_durations(cls, durations, values):
        if len(durations) != len(values["step_names"]):
            raise ValueError("Length of step durations must match length of step names")
        return durations

    @validator("lanes")
    def validate_lanes(cls, lanes, values):
        for lane in lanes:
            if len(lane) != len(values["step_names"]):
                raise ValueError(
                    f"Length of lane '{lane.name}' does not match length of steps"
                )
        return lanes

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

    def to_yaml(self) -> str:
        return YAMLSerializable.dump(self)
