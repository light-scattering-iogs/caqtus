from abc import ABC
from typing import TypeVar, Generic, Optional

import yaml
from pydantic import validator, root_validator

from expression import Expression
from settings_model import SettingsModel

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


class DigitalLane(Lane[bool]):
    pass


class Ramp(SettingsModel):
    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        """Build a python object from a YAML node

        Overload this method in a child class to change the default construction.
        """
        return cls()


class AnalogLane(Lane[Expression | Ramp]):
    units: str


class CameraAction(SettingsModel, ABC):
    pass


class TakePicture(CameraAction):
    picture_name: str


class CameraLane(Lane[Optional[CameraAction]]):
    """Lane to describe a camera

    The name of this lane must match one of the camera present in the experiment configuration.
    """

    @root_validator
    def validate_picture_names(cls, values):
        actions = values["values"]
        spans = values["spans"]
        name = values["name"]
        picture_names = set()
        for action, span in zip(actions, spans):
            if span > 0 and isinstance(action, TakePicture):
                if action.picture_name in picture_names:
                    raise ValueError(
                        f"Picture name {action.picture_name} is used twice in lane {name}"
                    )
                else:
                    picture_names.add(action.picture_name)
        return values

    def get_picture_spans(self) -> list[tuple[str, int, int]]:
        """Return a list of the pictures and the step index at which they start (included) and stop (excluded)"""
        result = []
        for action, start, stop in self.get_value_spans():
            if isinstance(action, TakePicture):
                result.append((action.picture_name, start, stop))
        return result

    def get_picture_names(self) -> list[str]:
        return [name for name, _, _ in self.get_picture_spans()]
