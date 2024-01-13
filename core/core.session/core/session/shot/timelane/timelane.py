import abc
import bisect
import itertools
from collections.abc import MutableSequence, Iterable, Sequence
from typing import TypeVar, Generic

import attrs

from core.types.expression import Expression

T = TypeVar("T")


@attrs.define(eq=False, repr=False)
class TimeLane(MutableSequence[T], abc.ABC, Generic[T]):
    # spanned_values[i] is the value of the lane at index i and the number of steps it
    # spans.
    _spanned_values: list[tuple[T, int]] = attrs.field()

    # _bounds[i] is the index at which spanned_values[i] starts (inclusive)
    # _bounds[i+1] is the index at which spanned_values[i] ends (exclusive)
    _bounds: list[int] = attrs.field(init=False, repr=False)

    def __attrs_post_init__(self):
        self._bounds = compute_bounds(span for _, span in self._spanned_values)

    def get_span(self, step: int) -> int:
        return self._spanned_values[step][1]

    def get_value(self, step: int) -> T:
        return self._spanned_values[step][0]

    def get_bounds(self, step: int) -> tuple[int, int]:
        return self._bounds[step], self._bounds[step + 1]

    def __len__(self):
        return self._bounds[-1]

    def __getitem__(self, item) -> T:
        if isinstance(item, int):
            return self.get_value_at_index(item)
        else:
            raise TypeError(f"Invalid type for index: {type(item)}")

    def get_value_at_index(self, index: int) -> T:
        index = normalize_index(index, len(self))
        if not (0 <= index < len(self)):
            raise IndexError(f"Index out of bounds: {index}")
        return self.get_value(find_containing_step(self._bounds, index))

    def __setitem__(self, key, value):
        if isinstance(key, int):
            self.set_value_at_index(key, value)
        else:
            raise TypeError(f"Invalid type for index: {type(key)}")

    def set_value_at_index(self, index: int, value: T):
        index = normalize_index(index, len(self))
        if not (0 <= index < len(self)):
            raise IndexError(f"Index out of bounds: {index}")
        step = find_containing_step(self._bounds, index)
        start, stop = self.get_bounds(step)
        before_length = index - start
        after_length = stop - index - 1
        previous_value = self.get_value(step)
        insert_index = step
        if before_length > 0:
            self._spanned_values.insert(insert_index, (previous_value, before_length))
            insert_index += 1
        self._spanned_values[insert_index] = (value, 1)
        insert_index += 1
        if after_length > 0:
            self._spanned_values.insert(insert_index, (previous_value, after_length))
        self._bounds = compute_bounds(span for _, span in self._spanned_values)

    def __delitem__(self, key):
        if isinstance(key, int):
            self.delete_index(key)
        else:
            raise TypeError(f"Invalid type for index: {type(key)}")

    def delete_index(self, index: int):
        del self.values[index]

    def insert(self, index: int, value: T):
        index = normalize_index(index, len(self))
        if index == len(self):
            self._spanned_values.append((value, 1))
            self._bounds.append(self._bounds[-1] + 1)
            return
        if not (0 <= index < len(self)):
            raise IndexError(f"Index out of bounds: {index}")
        step = find_containing_step(self._bounds, index)
        start, stop = self.get_bounds(step)
        before_length = index - start
        after_length = stop - index
        previous_value = self.get_value(step)
        insert_index = step
        if before_length > 0:
            self._spanned_values.insert(insert_index, (previous_value, before_length))
            insert_index += 1
        self._spanned_values[insert_index] = (value, 1)
        insert_index += 1
        if after_length > 0:
            self._spanned_values.insert(insert_index, (previous_value, after_length))
        self._bounds = compute_bounds(span for _, span in self._spanned_values)

    def __repr__(self):
        return f"{type(self).__name__}({self._spanned_values!r})"

    def __eq__(self, other):
        if isinstance(other, Sequence):
            if len(self) != len(other):
                return False
            return all(a == b for a, b in zip(self, other))
        else:
            return NotImplemented


def compute_bounds(spans: Iterable[int]) -> list[int]:
    return [0] + list(itertools.accumulate(spans))


def find_containing_step(bounds: Sequence[int], index: int) -> int:
    return bisect.bisect(bounds, index) - 1


def normalize_index(index: int, length: int) -> int:
    if index < 0:
        index = length + index
    return index


@attrs.define(eq=False, repr=False)
class DigitalTimeLane(TimeLane[bool | Expression]):
    pass


@attrs.define
class TimeLanes:
    step_names: list[str] = attrs.field(
        factory=list,
        validator=attrs.validators.deep_iterable(
            iterable_validator=attrs.validators.instance_of(list),
            member_validator=attrs.validators.instance_of(str),
        ),
        on_setattr=attrs.setters.validate,
    )
    step_durations: list[Expression] = attrs.field(
        factory=list,
        validator=attrs.validators.deep_iterable(
            iterable_validator=attrs.validators.instance_of(list),
            member_validator=attrs.validators.instance_of(Expression),
        ),
        on_setattr=attrs.setters.validate,
    )
    lanes: dict[str, TimeLane] = attrs.field(
        factory=dict,
        validator=attrs.validators.deep_mapping(
            key_validator=attrs.validators.instance_of(str),
            value_validator=attrs.validators.instance_of(TimeLane),
        ),
        on_setattr=attrs.setters.validate,
    )

    @property
    def number_steps(self) -> int:
        return len(self.step_names)

    @property
    def number_lanes(self) -> int:
        return len(self.lanes)
