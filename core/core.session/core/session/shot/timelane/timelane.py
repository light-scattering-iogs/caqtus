import abc
import bisect
import itertools
from collections.abc import MutableSequence, Iterable, Sequence
from typing import TypeVar, Generic, Self

import attrs

from core.types.expression import Expression
from util.asserts import assert_length_changed

T = TypeVar("T")


@attrs.define(init=False, eq=False, repr=False)
class TimeLane(MutableSequence[T], abc.ABC, Generic[T]):
    # spanned_values[i] is the value of the lane at index i and the number of steps it
    # spans.
    _spanned_values: list[tuple[T, int]] = attrs.field()

    # _bounds[i] is the index at which spanned_values[i] starts (inclusive)
    # _bounds[i+1] is the index at which spanned_values[i] ends (exclusive)
    _bounds: list[int] = attrs.field(init=False, repr=False)

    @_spanned_values.validator  # type: ignore
    def validate_spanned_values(self, _, value):
        if not value:
            raise ValueError("Spanned values must not be empty")
        if not all(span >= 1 for _, span in value):
            raise ValueError("Span must be at least 1")

    def __init__(self, values: Iterable[T]):
        """Initialize the lane with the given values.

        This constructor will group consecutive values that share the same id into
        blocks.

        This means that the following three lanes have the same blocks with length 3, 2,
        and 1:
        DigitalTimeLane([(True, 3), (False, 2), (True, 1)])
        DigitalTimeLane([True, True, True, False, False, True])
        DigitalTimeLane([True] * 3 + [False] * 2 + [True])

        Note however that the two following lanes are equivalent:
        AnalogTimeLane([Expression("...")] * 2 + [Expression("...")] * 3)
        AnalogTimeLane([(Expression("..."), 2), (Expression("..."), 3)])
        but are different from:
        AnalogTimeLane([Expression("...")] * 5)

        """

        values_list = list(values)
        spanned_values = []
        for value, group in itertools.groupby(values_list, key=id):
            g = list(group)
            spanned_values.append((g[0], len(g)))
        self._spanned_values = spanned_values
        self._bounds = compute_bounds(span for _, span in self._spanned_values)

    @classmethod
    def from_spanned_values(cls, spanned_values: Iterable[tuple[T, int]]) -> Self:
        obj = cls.__new__(cls)
        obj._spanned_values = list(spanned_values)
        obj._bounds = compute_bounds(span for _, span in obj._spanned_values)
        return obj

    def get_bounds(self, index: int) -> tuple[int, int]:
        index = normalize_index(index, len(self))
        if not (0 <= index < len(self)):
            raise IndexError(f"Index out of bounds: {index}")
        return self._get_block_bounds(find_containing_step(self._bounds, index))

    def values(self) -> Iterable[T]:
        return (value for value, _ in self._spanned_values)

    def bounds(self) -> Iterable[tuple[int, int]]:
        return zip(self._bounds[:-1], self._bounds[1:])

    def _get_containing_block(self, index: int) -> int:
        return find_containing_step(self._bounds, index)

    def _get_block_span(self, block: int) -> int:
        return self._spanned_values[block][1]

    def _get_block_value(self, block: int) -> T:
        return self._spanned_values[block][0]

    def _get_block_bounds(self, block: int) -> tuple[int, int]:
        return self._bounds[block], self._bounds[block + 1]

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
        return self._get_block_value(find_containing_step(self._bounds, index))

    def __setitem__(self, key, value):
        if isinstance(key, int):
            self.set_value_at_index(key, value)
        elif isinstance(key, slice):
            self.set_value_for_slice(key, value)
        else:
            raise TypeError(f"Invalid type for index: {type(key)}")

    def set_value_at_index(self, index: int, value: T):
        index = normalize_index(index, len(self))
        if not (0 <= index < len(self)):
            raise IndexError(f"Index out of bounds: {index}")
        step = find_containing_step(self._bounds, index)
        start, stop = self._get_block_bounds(step)
        before_length = index - start
        after_length = stop - index - 1
        previous_value = self._get_block_value(step)
        insert_index = step
        if before_length > 0:
            self._spanned_values.insert(insert_index, (previous_value, before_length))
            insert_index += 1
        self._spanned_values[insert_index] = (value, 1)
        insert_index += 1
        if after_length > 0:
            self._spanned_values.insert(insert_index, (previous_value, after_length))
        self._bounds = compute_bounds(span for _, span in self._spanned_values)

    def set_value_for_slice(self, slice_: slice, value: T):
        start = normalize_index(slice_.start, len(self))
        stop = normalize_index(slice_.stop, len(self))
        if not (0 <= start <= stop <= len(self)):
            raise IndexError(f"Slice out of bounds: {slice_}")
        if slice_.step is not None:
            raise ValueError(f"Slice step must be None: {slice_}")
        before_step = find_containing_step(self._bounds, start)
        before_length = start - self._get_block_bounds(before_step)[0]
        before_value = self._get_block_value(before_step)
        if stop == len(self):
            after_step = len(self._spanned_values) - 1
        else:
            after_step = find_containing_step(self._bounds, stop)
        after_length = self._get_block_bounds(after_step)[1] - stop
        after_value = self._get_block_value(after_step)
        del self._spanned_values[before_step : after_step + 1]
        insert_index = before_step
        if before_length > 0:
            self._spanned_values.insert(before_step, (before_value, before_length))
            insert_index += 1
        self._spanned_values.insert(insert_index, (value, stop - start))
        insert_index += 1
        if after_length > 0:
            self._spanned_values.insert(insert_index, (after_value, after_length))
        self._bounds = compute_bounds(span for _, span in self._spanned_values)

    def __delitem__(self, key):
        if isinstance(key, int):
            self.delete_index(key)
        else:
            raise TypeError(f"Invalid type for index: {type(key)}")

    @assert_length_changed(-1)
    def delete_index(self, index: int):
        """Delete a single index from the lane.

        The length of the lane is always exactly one less after this operation.
        """

        previous_length = len(self)

        index = normalize_index(index, len(self))
        if not (0 <= index < len(self)):
            raise IndexError(f"Index out of bounds: {index}")
        block = find_containing_step(self._bounds, index)
        if self._get_block_span(block) == 1:
            del self._spanned_values[block]
        else:
            self._spanned_values[block] = (
                self._get_block_value(block),
                self._get_block_span(block) - 1,
            )
        self._bounds = compute_bounds(span for _, span in self._spanned_values)
        assert len(self) == previous_length - 1

    @assert_length_changed(+1)
    def insert(self, index: int, value: T):
        index = normalize_index(index, len(self))
        if index == len(self):
            self._spanned_values.append((value, 1))
            self._bounds.append(self._bounds[-1] + 1)
            return
        if not (0 <= index < len(self)):
            raise IndexError(f"Index out of bounds: {index}")
        step = find_containing_step(self._bounds, index)
        start, stop = self._get_block_bounds(step)
        before_length = index - start
        after_length = stop - index
        previous_value = self._get_block_value(step)
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
        to_concatenate = []
        for length, group in itertools.groupby(
            self._spanned_values, key=lambda x: x[1]
        ):
            if length == 1:
                to_concatenate.append(
                    f"[{', '.join(repr(value) for value, _ in group)}]"
                )
            else:
                to_concatenate.extend(
                    [f"[{repr(value)}] * {length}" for value, _ in group]
                )
        formatted = " + ".join(to_concatenate)
        return f"{type(self).__name__}({formatted})"

    def __eq__(self, other):
        if isinstance(other, TimeLane):
            return self._spanned_values == other._spanned_values
        elif isinstance(other, Sequence):
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


@attrs.define
class TimeLanes:
    """A collection of time lanes."""


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
        """The number of steps in the time lanes.

        The number of steps is the same as the length of each lane.
        """

        return len(self.step_names)

    @property
    def number_lanes(self) -> int:
        """Returns the number of lanes."""

        return len(self.lanes)

    def __setitem__(self, name: str, lane: TimeLane):
        """Sets the value of a lane.

        Raises:
            TypeError: If the lane value is not an instance of TimeLane.
            TypeError: If the lane name is not a string.
            ValueError: If the lane value has a different length than the other lanes.
        """

        if not isinstance(lane, TimeLane):
            raise TypeError(f"Invalid type for value: {type(lane)}")
        if not isinstance(name, str):
            raise TypeError(f"Invalid type for key: {type(name)}")
        length = len(lane)
        if not all(length == len(l) for l in self.lanes.values()):
            raise ValueError("All lanes must have the same length")

        self.lanes[name] = lane

    def __getitem__(self, key: str) -> TimeLane:
        """Returns the value of a lane.

        Raises:
            KeyError: If the lane name is not found.
        """

        return self.lanes[key]
