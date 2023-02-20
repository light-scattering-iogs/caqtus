import logging
from abc import ABC
from copy import copy
from typing import TypeVar, Generic, Optional

import yaml
from pydantic import validator

from expression import Expression
from settings_model import SettingsModel
from units import dimensionless, Quantity

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

T = TypeVar("T")

TLane = TypeVar("TLane", bound="Lane")


class Lane(Generic[T], SettingsModel):
    """Represents a temporal list of actions spread over steps that a device can do

    Some actions may span over several steps and values that have a span of 0 are ignored.
    ex: values = (1, 2, 3, 4, 5)
        spans  = (1, 2, 0, 1, 1)
    is equivalent to the time series  of values (1, 2, 2, 4, 5).

    This is a generic class that implement arbitrary actions type T. It should be subclassed for specific action types.
    """

    name: str
    spans: tuple[int, ...]
    values: tuple[T, ...]

    @validator("spans")
    def validate_spans(cls, spans: tuple[int, ...]):
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

    @validator("values")
    def validate_values(cls, lane_values, values):
        lane_values = list(lane_values)
        spans = values["spans"]
        if len(spans) != len(lane_values):
            raise ValueError("Length of spans and values must match")
        index = 0
        while index < len(spans):
            if spans[index] >= 1:
                span = spans[index]
                value = lane_values[index]
                for index in range(index + 1, index + span):
                    if spans[index] == 0:
                        lane_values[index] = copy(value)
                    else:
                        raise ValueError(f"Span at position {index} should be zero")
                index += 1
            else:
                raise ValueError(f"Span at position {index} should be larger than 1")
        return tuple(lane_values)

    def __len__(self) -> int:
        return len(self.values)

    def insert(self, index: int, value: T):
        new_values = list(self.values)
        new_spans = list(self.spans)
        if index >= len(self) or self.spans[index] != 0:
            new_values.insert(index, copy(value))
            new_spans.insert(index, 1)
        elif self.spans[index] == 0:
            spanner = self._find_spanner(index)
            new_spans[spanner] += 1
            new_values.insert(index, copy(self.values[spanner]))
            new_spans.insert(index, 0)
        self.spans = tuple(new_spans)
        self.values = tuple(new_values)

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
        self.spans = tuple(new_spans)
        self.values = tuple(new_values)

    def _find_spanner(self, index):
        i = index
        while self.spans[i] == 0:
            i -= 1
        return i

    def merge(self, start, stop):
        """Merge the cells between start included and stop excluded"""
        new_spans = list(self.spans)
        new_values = list(self.values)
        start, _ = self.span(start)
        _, stop = self.span(stop - 1)
        total_span = sum(self.spans[start:stop])
        for i in range(start, stop):
            new_spans[i] = 0
            new_values[i] = copy(self.values[start])
        new_spans[start] = total_span
        self.spans = tuple(new_spans)
        self.values = tuple(new_values)

    def break_(self, start, stop):
        new_spans = list(self.spans)
        new_values = list(self.values)
        start, _ = self.span(start)
        _, stop = self.span(stop - 1)
        for i in range(start, stop):
            new_spans[i] = 1
            new_values[i] = copy(self.values[start])
        self.spans = tuple(new_spans)
        self.values = tuple(new_values)

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

    def get_value_spans(self) -> list[tuple[T, int, int]]:
        """Return a list of values with their respective spans

        It has the form [(value0, start0, stop0), (value1, start1, stop1), ...], where stop is excluded for each value.
        """

        result = []
        index = 0
        while index < len(self.values):
            value = self.values[index]
            start = index
            index += 1
            while index < len(self.values) and self.spans[index] == 0:
                index += 1
            stop = index
            result.append((value, start, stop))
        return result

    def span(self, index) -> tuple[int, int]:
        start = self._find_spanner(index)
        stop = start + self.spans[start]
        return start, stop


class DigitalLane(Lane[bool]):
    pass


class Ramp(SettingsModel, ABC):
    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        """Build a ramp object from a YAML node"""
        return cls()

    @classmethod
    def representer(cls, dumper: yaml.Dumper, ramp: "Ramp"):
        """Represent a ramp object with a yaml string with no value"""

        return dumper.represent_scalar(f"!{cls.__name__}", "")


class LinearRamp(Ramp):
    pass


class AnalogLane(Lane[Expression | Ramp]):
    units: str

    def has_dimension(self) -> bool:
        return not Quantity(1, units=self.units).is_compatible_with(dimensionless)


class CameraAction(SettingsModel, ABC):
    pass


class TakePicture(CameraAction):
    picture_name: str


class CameraLane(Lane[Optional[CameraAction]]):
    """Lane to describe a camera

    The name of this lane must match one of the camera present in the experiment configuration.
    """

    @validator("values")
    def validate_values(cls, actions, values):
        """Check that there are not two separate pictures with the same name"""

        actions = super().validate_values(actions, values)
        spans = values["spans"]
        name = values["name"]
        picture_names = set()
        for action, span in zip(actions, spans):
            if span > 0 and isinstance(action, TakePicture):
                if action.picture_name in picture_names:
                    raise ValueError(
                        f"Picture name '{action.picture_name} is used twice in lane '{name}'"
                    )
                else:
                    picture_names.add(action.picture_name)
        return actions

    def get_picture_spans(self) -> list[tuple[str, int, int]]:
        """Return a list of the pictures and the step index at which they start (included) and stop (excluded)"""

        result = []
        for action, start, stop in self.get_value_spans():
            if isinstance(action, TakePicture):
                result.append((action.picture_name, start, stop))
        return result

    def get_picture_names(self) -> list[str]:
        return [name for name, _, _ in self.get_picture_spans()]
