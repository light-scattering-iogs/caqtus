from typing import Generic, TypeVar

from pydantic import validator

from expression import Expression
from settings_model import SettingsModel
import logging

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

T = TypeVar("T")


class Lane(Generic[T], SettingsModel):
    """Represents a temporal list of actions spread over steps that a device can do

    Some actions may span over several steps.
    ex: values = [1, 2, 3, 4, 5]
        spans  = [1, 2, 0, 1, 1]
    is equivalent to the time series [1, 2, 2, 4, 5].
    """

    name: str
    values: list[T]
    spans: list[int]

    def __len__(self):
        return len(self.values)

    def insert(self, index: int, value: T):
        if index >= len(self) or self.spans[index] != 0:
            self.values.insert(index, value)
            self.spans.insert(index, 1)
        elif self.spans[index] == 0:
            spanner = self._find_spanner(index)
            self.spans[spanner] += 1
            self.values.insert(index, self.values[spanner])
            self.spans.insert(index, 0)

    def remove(self, index):
        if self.spans[index] == 0:
            spanner = self._find_spanner(index)
            self.spans[spanner] -= 1
        if self.spans[index] > 1:
            self.spans[index + 1] = self.spans[index] - 1
        self.values.pop(index)
        self.spans.pop(index)

    def _find_spanner(self, index):
        i = index - 1
        while self.spans[i] == 0:
            i -= 1
        return i

    def merge(self, start, stop):
        total_span = sum(self.spans[start:stop])
        for i in range(start, stop):
            self.spans[i] = 0
        self.spans[start] = total_span

    def break_(self, start, stop):
        for i in range(start, stop):
            self.spans[i] = 1

    def get_effective_value(self, index):
        if self.spans[index] != 0:
            return self.values[index]
        else:
            return self.values[self._find_spanner(index)]


class DigitalLane(Lane[bool]):
    pass


class Ramp(SettingsModel):
    pass


class LinearRamp(SettingsModel):
    pass


class AnalogLane(Lane[Expression | Ramp]):
    pass


class CameraLane(Lane[bool]):
    pass


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
