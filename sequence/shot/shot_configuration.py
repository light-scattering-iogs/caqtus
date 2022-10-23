from typing import Generic, TypeVar

from pydantic import validator

from expression import Expression
from settings_model import SettingsModel

T = TypeVar("T")


class Lane(SettingsModel, Generic[T]):
    """Represents a temporal list of actions spread over steps that a device can do

    Some actions may span over several steps.
    """
    name: str
    values: list[T]
    spans: list[int]

    def __len__(self):
        return len(self.values)


class ShotConfiguration(SettingsModel):
    step_names: list[str]
    step_durations: list[Expression]
    lanes: list[Lane]

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
