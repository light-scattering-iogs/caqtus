import logging
from typing import Generic, TypeVar, Optional

from pydantic import validator

from expression import Expression
from settings_model import SettingsModel

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

T = TypeVar("T")


class Lane(Generic[T], SettingsModel):
    """Represents a temporal list of actions spread over steps that a device can do

    Some actions may span over several steps and values that have a span of 0 are ignored.
    ex: values = (1, 2, 3, 4, 5)
        spans  = (1, 2, 0, 1, 1)
    is equivalent to the time series  of values (1, 2, 2, 4, 5).
    """

    name: str
    values: tuple[T, ...]
    spans: tuple[int, ...]

    @validator("spans")
    def validate_spans(cls, spans: tuple[int, ...], values):
        if len(spans) != len(values["values"]):
            raise ValueError("Length of spans and values must match")
        index = 0
        while index < len(spans):
            if spans[index] >= 1:
                span = spans[index]
                for index in range(index + 1, index + span):
                    if spans[index] != 0:
                        raise ValueError(f"Span at position {index} should be zero")
                index += 1
            else:
                raise ValueError(f"Span at position {index} should be larger than 1")
        return spans

    def __len__(self) -> int:
        return len(self.values)

    def insert(self, index: int, value: T):
        new_values = list(self.values)
        new_spans = list(self.spans)
        if index >= len(self) or self.spans[index] != 0:
            new_values.insert(index, value)
            new_spans.insert(index, 1)
        elif self.spans[index] == 0:
            spanner = self._find_spanner(index)
            new_spans[spanner] += 1
            new_values.insert(index, self.values[spanner])
            new_spans.insert(index, 0)
        self.values = tuple(new_values)
        self.spans = tuple(new_spans)

    def remove(self, index):
        new_values = list(self.values)
        new_spans = list(self.spans)
        if self.spans[index] == 0:
            spanner = self._find_spanner(index)
            new_spans[spanner] -= 1
        elif self.spans[index] > 1:
            new_spans[index + 1] = self.spans[index] - 1
        new_values.pop(index)
        new_spans.pop(index)
        self.values = tuple(new_values)
        self.spans = tuple(new_spans)

    def _find_spanner(self, index):
        i = index
        while self.spans[i] == 0:
            i -= 1
        return i

    def merge(self, start, stop):
        new_spans = list(self.spans)
        total_span = sum(self.spans[start:stop])
        for i in range(start, stop):
            new_spans[i] = 0
        new_spans[start] = total_span
        self.spans = tuple(new_spans)

    def break_(self, start, stop):
        new_spans = list(self.spans)
        for i in range(start, stop):
            new_spans[i] = 1
        self.spans = tuple(new_spans)

    def __setitem__(self, key, value):
        new_values = list(self.values)
        new_values[self._find_spanner(key)] = value
        self.values = tuple(new_values)

    def __getitem__(self, item) -> T:
        return self.get_effective_value(item)

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
    units: str


class CameraLane(Lane[Optional[str]]):
    """Lane to describe a camera

    The name of this lane must match one of the camera present in the experiment configuration. Values in the lane
    that have a string value indicates that the camera should take a picture during these steps and the picture name
    corresponds to the string value. If the cell value is None, the camera is not exposing.
    """


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
