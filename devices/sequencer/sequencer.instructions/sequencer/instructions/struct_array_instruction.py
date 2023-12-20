from __future__ import annotations

import abc
import bisect
from typing import (
    NewType,
    TypeVar,
    Generic,
    overload,
    Optional,
    assert_never,
    Self,
    SupportsInt,
)

import numpy
import numpy as np
from numpy.lib.recfunctions import merge_arrays
from numpy.typing import DTypeLike

Length = NewType("Length", int)
Width = NewType("Width", int)
Depth = NewType("Depth", int)

_T = TypeVar("_T")


class SequencerInstruction(abc.ABC, Generic[_T]):
    """An immutable representation of instructions to output on a sequencer.

    This represents a high-level series of instructions to output on a sequencer. Each instruction is a compact
    representation of values to output at integer time steps. The length of the instruction is the number of time steps
    it takes to output all the values. The width of the instruction is the number of channels that are output at each
    time step.
    """

    @abc.abstractmethod
    def __len__(self) -> Length:
        """Returns the length of the instruction in clock cycles."""

        raise NotImplementedError

    @overload
    def __getitem__(self, item: int) -> _T:
        ...

    @overload
    def __getitem__(self, item: slice) -> SequencerInstruction[_T]:
        ...

    @abc.abstractmethod
    def __getitem__(self, item: int | slice) -> _T | SequencerInstruction[_T]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def dtype(self) -> numpy.dtype:
        """Returns the dtype of the instruction."""

        raise NotImplementedError

    @abc.abstractmethod
    def as_type(self, dtype: numpy.dtype) -> SequencerInstruction:
        """Returns a new instruction with the given dtype."""

        raise NotImplementedError

    @property
    @abc.abstractmethod
    def width(self) -> Width:
        """Returns the number of parallel channels that are output at each time step."""

        raise NotImplementedError

    @property
    @abc.abstractmethod
    def depth(self) -> Depth:
        """Returns the number of nested instructions.

        The invariant `instruction.depth <= len(instruction)` always holds.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def to_pattern(self) -> Pattern:
        """Returns a flattened pattern of the instruction."""

        raise NotImplementedError

    @abc.abstractmethod
    def __eq__(self, other):
        raise NotImplementedError

    @classmethod
    def empty_like(
        cls, instruction: SequencerInstruction[_T]
    ) -> SequencerInstruction[_T]:
        return Pattern([], dtype=instruction.dtype)

    def __add__(self, other) -> SequencerInstruction[_T]:
        if isinstance(other, SequencerInstruction):
            if len(self) == 0:
                return other
            elif len(other) == 0:
                return self
            else:
                return Concatenate(self, other)
        else:
            return NotImplemented

    def __mul__(self, other):
        if isinstance(other, int):
            if other < 0:
                raise ValueError("Repetitions must be a positive integer")
            elif other == 0:
                return self.empty_like(self)
            elif other == 1:
                return self
            else:
                return Repeat(other, self)
        else:
            return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)

    @abc.abstractmethod
    def get_channel(self, channel: str) -> SequencerInstruction:
        """Returns the instruction for the given channel."""

        raise NotImplementedError

    @classmethod
    def _create_pattern_without_copy(cls, array: np.array) -> Pattern:
        array.setflags(write=False)
        pattern = Pattern.__new__(Pattern)
        pattern._pattern = array
        return pattern


class Pattern(SequencerInstruction):
    __slots__ = ("_pattern",)
    """An instruction to output a pattern on a sequencer."""

    def __init__(self, pattern, dtype: Optional[DTypeLike] = None):
        self._pattern = numpy.array(pattern, dtype=dtype)
        self._pattern.setflags(write=False)

    def __repr__(self):
        return f"Pattern({list(self._pattern)!r})"

    def __str__(self):
        return str(self._pattern)

    def __getitem__(self, item):
        if isinstance(item, int):
            return self._pattern[item]
        elif isinstance(item, slice):
            # Here we don't create a new pattern through the constructor, because we want to avoid copying the
            # underlying numpy array. Instead, we create a new pattern and set its internal numpy array to a view of the
            # original pattern's array.
            new_pattern = object.__new__(type(self))
            new_pattern._pattern = self._pattern[
                item
            ]  # in numpy, slicing creates a view, so we don't copy here
            return new_pattern
        else:
            assert_never(item)

    @property
    def dtype(self) -> numpy.dtype:
        return self._pattern.dtype

    def as_type(self, dtype: numpy.dtype) -> Self:
        # Here we try to avoid copy if possible.
        new_pattern = object.__new__(type(self))
        new_pattern._pattern = self._pattern.astype(dtype, copy=False)
        return new_pattern

    def __len__(self) -> Length:
        return Length(len(self._pattern))

    @property
    def width(self) -> Width:
        fields = self.dtype.fields
        if fields is None:
            return Width(1)
        else:
            return Width(len(fields))

    @property
    def depth(self) -> Depth:
        return Depth(0)

    def to_pattern(self) -> Pattern:
        return self

    def __eq__(self, other):
        if isinstance(other, Pattern):
            return numpy.array_equal(self._pattern, other._pattern)
        else:
            return NotImplemented

    def merge_channels(self, other: SequencerInstruction[_T]) -> Pattern:
        if len(self) != len(other):
            raise ValueError("Instructions must have the same length")
        other_pattern = other.to_pattern()
        merged = merge_arrays(
            [self._pattern, other_pattern._pattern], flatten=True, fill_value=None
        )
        return self._create_pattern_without_copy(merged)

    def get_channel(self, channel: str) -> SequencerInstruction:
        return self._create_pattern_without_copy(self._pattern[channel])


class Concatenate(SequencerInstruction[_T]):
    __slots__ = ("_instructions", "_instruction_bounds")
    __match_args__ = ("instructions",)

    def __init__(self, *instructions: SequencerInstruction[_T]):
        """Creates a new instruction that is the concatenation of the given instructions.

        Args:
            instructions: The instructions to concatenate.
                It must contain at least two instructions.
                All instructions must have a lengths strictly greater than zero.
                All instructions must have the same dtype.
        """

        instructions_list: list[SequencerInstruction[_T]] = []
        for instruction in instructions:
            match instruction:
                case Concatenate(instructions):
                    # We treat concatenation of concatenations as a single concatenation to avoid nesting and increasing
                    # the depth of the instruction tree.
                    instructions_list.extend(instructions)
                case SequencerInstruction():
                    instructions_list.append(instruction)
                case _:
                    assert_never(instruction)

        self._instructions = tuple(instructions_list)
        if len(self._instructions) < 2:
            raise ValueError(
                "Concatenate instructions must have at least two instructions"
            )
        dtype = self._instructions[0].dtype
        for index, instruction in enumerate(self._instructions):
            if len(instruction) == 0:
                raise ValueError(
                    f"Cannot concatenate empty instruction at index {index}"
                )
            if instruction.dtype != dtype:
                raise TypeError(
                    f"Instruction at index {index} has dtype {instruction.dtype}, expected {dtype}"
                )
        # self._instruction_bounds[i] is the first element index (included) the i-th instruction
        # self._instruction_bounds[i+1] is the last element index (excluded) of the i-th instruction
        self._instruction_bounds = np.concatenate(
            [
                np.array([0]),
                numpy.cumsum([len(instruction) for instruction in self._instructions]),
            ]
        )

    @property
    def instructions(self) -> tuple[SequencerInstruction[_T], ...]:
        return self._instructions

    def __repr__(self):
        inner = ", ".join(repr(instruction) for instruction in self._instructions)
        return f"Concatenate({inner})"

    def __str__(self):
        sub_strings = [
            str(instruction) if instruction.depth == 0 else f"({instruction!s})"
            for instruction in self._instructions
        ]
        return " + ".join(sub_strings)

    def __getitem__(self, item):
        match item:
            case int() as index:
                return self._get_index(index)
            case slice() as slice_:
                return self._get_slice(slice_)
            case _:
                assert_never(item)

    def _get_index(self, index: int) -> _T:
        index = _normalize_index(index, len(self))
        instruction_index = bisect.bisect_left(self._instruction_bounds, index)
        instruction = self._instructions[instruction_index]
        instruction_start_index = self._instruction_bounds[instruction_index]
        return instruction[index - instruction_start_index]

    def _get_slice(self, slice_: slice) -> SequencerInstruction[_T]:
        start, stop, step = _normalize_slice(slice_, len(self))
        if step != 1:
            raise NotImplementedError
        start_step_index = (
            numpy.searchsorted(self._instruction_bounds, start, side="right") - 1
        )
        stop_step_index = (
            numpy.searchsorted(self._instruction_bounds, stop, side="left") - 1
        )

        result = self.empty_like(self._instructions[0])
        for instruction_index in range(start_step_index, stop_step_index + 1):
            instruction_start_index = int(self._instruction_bounds[instruction_index])
            instruction_slice_start = max(start, instruction_start_index)
            instruction_stop_index = int(
                self._instruction_bounds[instruction_index + 1]
            )
            instruction_slice_stop = min(stop, instruction_stop_index)
            instruction_slice = slice(
                instruction_slice_start - instruction_start_index,
                instruction_slice_stop - instruction_start_index,
                step,
            )
            result += self._instructions[instruction_index][instruction_slice]
        return result

    @property
    def dtype(self) -> numpy.dtype:
        return self._instructions[0].dtype

    def as_type(self, dtype: numpy.dtype) -> Self:
        return type(self)(
            *(instruction.as_type(dtype) for instruction in self._instructions)
        )

    def __len__(self) -> Length:
        return Length(sum(len(instruction) for instruction in self._instructions))

    @property
    def width(self) -> Width:
        return self._instructions[0].width

    @property
    def depth(self) -> Depth:
        return Depth(max(instruction.depth for instruction in self._instructions) + 1)

    def to_pattern(self) -> Pattern:
        # noinspection PyProtectedMember
        new_array = numpy.concatenate(
            [instruction.to_pattern()._pattern for instruction in self._instructions],
            casting="safe",
        )
        return self._create_pattern_without_copy(new_array)

    def __eq__(self, other):
        if isinstance(other, Concatenate):
            return self._instructions == other._instructions
        else:
            return NotImplemented

    def get_channel(self, channel: str) -> SequencerInstruction:
        return Concatenate(
            *(instruction.get_channel(channel) for instruction in self._instructions)
        )


class Repeat(SequencerInstruction[_T]):
    __slots__ = ("_repetitions", "_instruction")

    @property
    def repetitions(self) -> int:
        return self._repetitions

    @property
    def instruction(self) -> SequencerInstruction[_T]:
        return self._instruction

    def __init__(self, repetitions: SupportsInt, instruction: SequencerInstruction[_T]):
        rep = int(repetitions)
        if rep < 2:
            raise ValueError("Repetitions must be greater than or equal to 2")
        if len(instruction) < 1:
            raise ValueError("Instruction must have a length greater than 0")
        match instruction:
            # We merge repetitions of repetitions into a single repetition to avoid nesting and increasing the depth of
            # the instruction tree.
            case Repeat(repetitions=inner_rep, instruction=inner_instruction):
                self._repetitions = rep * inner_rep
                self._instruction = inner_instruction
            case SequencerInstruction():
                self._repetitions = rep
                self._instruction = instruction
            case _:
                assert_never(instruction)

    def __repr__(self):
        return f"Repeat(repetitions={self._repetitions!r}, instruction={self._instruction!r})"

    def __str__(self):
        return f"{self._repetitions} * {self._instruction!s}"

    def __len__(self) -> Length:
        return Length(len(self._instruction) * self._repetitions)

    def __getitem__(self, item):
        if isinstance(item, int):
            return self._get_index(item)
        elif isinstance(item, slice):
            return self._get_slice(item)
        else:
            assert_never(item)

    def _get_index(self, index: int) -> _T:
        index = _normalize_index(index, len(self))
        _, r = divmod(index, len(self._instruction))
        return self._instruction[r]

    def _get_slice(self, slice_: slice) -> SequencerInstruction[_T]:
        start, stop, step = _normalize_slice(slice_, len(self))
        if step != 1:
            raise NotImplementedError
        q_start, r_start = divmod(start, len(self._instruction))
        q_stop, r_stop = divmod(stop, len(self._instruction))
        if q_start == q_stop:
            return self._instruction[r_start:r_stop:step]
        else:
            prepend = self._instruction[r_start::step]
            append = self._instruction[:r_stop:step]
            middle = (q_stop - q_start - 1) * self._instruction
            return prepend + middle + append

    @property
    def dtype(self) -> numpy.dtype:
        return self._instruction.dtype

    def as_type(self, dtype: numpy.dtype) -> SequencerInstruction:
        return type(self)(self._repetitions, self._instruction.as_type(dtype))

    @property
    def width(self) -> Width:
        return self._instruction.width

    @property
    def depth(self) -> Depth:
        return Depth(self._instruction.depth + 1)

    def to_pattern(self) -> Pattern:
        inner_pattern = self._instruction.to_pattern()
        # noinspection PyProtectedMember
        new_array = numpy.tile(inner_pattern._pattern, self._repetitions)
        return self._create_pattern_without_copy(new_array)

    def __eq__(self, other):
        if isinstance(other, Repeat):
            return (
                self._repetitions == other._repetitions
                and self._instruction == other._instruction
            )
        else:
            return NotImplemented

    def get_channel(self, channel: str) -> SequencerInstruction:
        return Repeat(self._repetitions, self._instruction.get_channel(channel))


def _normalize_index(index: int, length: int) -> int:
    normalized = index if index >= 0 else length + index
    if not 0 <= normalized < length:
        raise IndexError(f"Index {index} is out of bounds for length {length}")
    return normalized


def _normalize_slice_index(index: int, length: int) -> int:
    normalized = index if index >= 0 else length + index
    if not 0 <= normalized <= length:
        raise IndexError(f"Slice index {index} is out of bounds for length {length}")
    return normalized


def _normalize_slice(slice_: slice, length: int) -> tuple[int, int, int]:
    step = slice_.step or 1
    if step == 0:
        raise ValueError("Slice step cannot be zero")
    if slice_.start is None:
        start = 0 if step > 0 else length - 1
    else:
        start = _normalize_slice_index(slice_.start, length)
    if slice_.stop is None:
        stop = length if step > 0 else -1
    else:
        stop = _normalize_slice_index(slice_.stop, length)

    return start, stop, step
