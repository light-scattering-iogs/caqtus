from __future__ import annotations

import abc
import bisect
import collections
import itertools
import math
from collections.abc import Sequence
from typing import (
    NewType,
    TypeVar,
    overload,
    Optional,
    assert_never,
    Callable,
)

import numpy
import numpy as np
import numpy.typing as npt
from numpy.typing import DTypeLike

Length = NewType("Length", int)
Width = NewType("Width", int)
Depth = NewType("Depth", int)

_S = TypeVar("_S", covariant=True, bound=DTypeLike)

type Array1D[T] = npt.NDArray[T]


class SequencerInstruction[T: np.generic](abc.ABC):
    """An immutable representation of instructions to output on a sequencer.

    This represents a high-level series of instructions to output on a sequencer.
    Each instruction is a compact representation of values to output at integer time
    steps.
    The length of the instruction is the number of time steps it takes to output all
    the values.
    The width of the instruction is the number of channels that are output at each time
    step.

    Instructions can be concatenated in time using the `+` operator or the
    :func:`concatenate`.
    An instruction can be repeated using the `*` operator with an integer.
    """

    @abc.abstractmethod
    def __len__(self) -> Length:
        """Returns the length of the instruction in clock cycles."""

        raise NotImplementedError

    @overload
    def __getitem__(self, item: int) -> T:
        """Returns the value at the given index."""

        ...

    @overload
    def __getitem__(self, item: slice) -> SequencerInstruction[T]:
        """Returns a sub-instruction over the given slice.

        Warning:
            Not all valid slices are supported.
            Only slices with a step of 1 are fully supported for all instructions.
        """

        ...

    @overload
    def __getitem__[S: np.generic](self, item: str) -> SequencerInstruction[S]:
        """Returns a sub-instruction over the given field.

        Returns:
            A new instruction with the given field.
            This new instruction has the same length as the original instruction.

        Raises:
            ValueError: If the instruction does not have fields or the field is not
            found.
        """

        ...

    @abc.abstractmethod
    def __getitem__(self, item):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def dtype(self) -> numpy.dtype[T]:
        """Returns the dtype of the instruction."""

        raise NotImplementedError

    @abc.abstractmethod
    def as_type[S: np.generic](self, dtype: numpy.dtype[S]) -> SequencerInstruction[S]:
        """Returns a new instruction with the given dtype."""

        raise NotImplementedError

    @property
    def width(self) -> Width:
        """Returns the number of parallel channels that are output at each time step."""

        fields = self.dtype.fields
        if fields is None:
            return Width(1)
        else:
            return Width(len(fields))

    @property
    @abc.abstractmethod
    def depth(self) -> Depth:
        """Returns the number of nested instructions.

        The invariant `instruction.depth <= len(instruction)` always holds.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def to_pattern(self) -> Pattern[T]:
        """Returns a flattened pattern of the instruction."""

        raise NotImplementedError

    @abc.abstractmethod
    def __eq__(self, other):
        raise NotImplementedError

    def __add__(self, other) -> SequencerInstruction[T]:
        if isinstance(other, SequencerInstruction):
            if len(self) == 0:
                return other
            elif len(other) == 0:
                return self
            else:
                return concatenate(self, other)
        else:
            return NotImplemented

    def __mul__(self, other) -> SequencerInstruction[T]:
        if isinstance(other, int):
            if other < 0:
                raise ValueError("Repetitions must be a positive integer")
            elif other == 0:
                return empty_like(self)
            elif other == 1:
                return self
            else:
                if isinstance(self, Repeated):
                    return Repeated(self._repetitions * other, self._instruction)
                else:
                    return Repeated(other, self)
        else:
            # We specifically raise an error here and not return NotImplemented to avoid
            # multiplication by a numpy integer taking over and returning a numpy
            # array instead of a SequencerInstruction.
            raise TypeError(f"Cannot multiply instruction by {other!r}")

    def __rmul__(self, other) -> SequencerInstruction[T]:
        return self.__mul__(other)

    @abc.abstractmethod
    def apply[
        S: np.generic
    ](self, func: Callable[[Array1D[T]], Array1D[S]]) -> SequencerInstruction[S]:
        """Applies an element-wise function to the values of the instruction.

        Args:
            func: The function to apply to the values of the instruction.
                It must take a 1D numpy array with the same dtype as the instruction
                and return a 1D numpy array with the same length and a (possibly)
                different dtype.

        Returns:
            A new instruction with the function applied to the values.
            The length of the new instruction is the same as the original instruction.

        Raises:
            ValueError: If the function does not return an array of the same length as
                the one given.
        """

        raise NotImplementedError

    def _repr_mimebundle_(self, include=None, exclude=None):
        from ._to_graph import to_graph

        graph = to_graph(self)
        return graph._repr_mimebundle_(include, exclude)


class Pattern[T: np.generic](SequencerInstruction[T]):
    """An instruction representing a sequence of values.

    This is a fully explicit instruction for which each sample point must be given.
    """

    __slots__ = ("_pattern", "_length")

    def __init__(self, pattern: npt.ArrayLike, dtype: Optional[np.dtype[T]] = None):
        self._pattern = numpy.array(pattern, dtype=dtype)
        self._pattern.setflags(write=False)
        self._length = Length(len(self._pattern))

    def __repr__(self):
        return f"Pattern({self._pattern.tolist()!r})"

    def __str__(self):
        return str(self._pattern.tolist())

    @overload
    def __getitem__(self, item: int) -> T: ...

    @overload
    def __getitem__(self, item: slice) -> Pattern[T]: ...

    @overload
    def __getitem__[S: np.generic](self, item: str) -> SequencerInstruction[S]: ...

    def __getitem__(self, item):
        if isinstance(item, int):
            return self._pattern[item]
        elif isinstance(item, slice):
            return Pattern.create_without_copy(self._pattern[item])
        elif isinstance(item, str):
            return Pattern.create_without_copy(self._pattern[item])
        else:
            assert_never(item)

    @classmethod
    def create_without_copy[S: np.generic](cls, array: Array1D[S]) -> Pattern[S]:
        array.setflags(write=False)
        pattern = cls.__new__(cls)
        pattern._pattern = array
        pattern._length = Length(len(array))
        return pattern  # type: ignore

    @property
    def dtype(self) -> numpy.dtype[T]:
        return self._pattern.dtype

    def as_type[S: np.generic](self, dtype: numpy.dtype[S]) -> Pattern[S]:
        return Pattern.create_without_copy(self._pattern.astype(dtype, copy=False))

    def __len__(self) -> Length:
        return self._length

    @property
    def depth(self) -> Depth:
        return Depth(0)

    def to_pattern(self) -> Pattern[T]:
        return self

    def __eq__(self, other):
        if isinstance(other, Pattern):
            return numpy.array_equal(self._pattern, other._pattern)
        else:
            return NotImplemented

    def apply[
        S: np.generic
    ](self, func: Callable[[Array1D[T]], Array1D[S]]) -> Pattern[S]:
        result = func(self._pattern)
        if len(result) != len(self):
            raise ValueError("Function must return an array of the same length")
        return Pattern.create_without_copy(result)

    @property
    def array(self) -> Array1D[T]:
        return self._pattern


class Concatenated[T: np.generic](SequencerInstruction[T]):
    """Represents an immutable concatenation of instructions.

    Use the `+` operator or the function :func:`concatenate` to concatenate instructions.
    Do not use the class constructor directly.

    Attributes:
        instructions: The instructions concatenated by this instruction.
            This instruction is equivalent to chaining the instructions in this list
            one after the other.
    """

    __slots__ = ("_instructions", "_instruction_bounds", "_length")
    __match_args__ = ("instructions",)

    @property
    def instructions(self) -> tuple[SequencerInstruction[T], ...]:
        """The instructions concatenated by this instruction."""

        return self._instructions

    def __init__(self, *instructions: SequencerInstruction[T]):
        assert all(
            isinstance(instruction, SequencerInstruction)
            for instruction in instructions
        )
        # The following assertions define a "pure" concatenation.
        # (i.e. no empty instructions, no nested concatenations, and at least two
        # instructions).
        assert all(len(instruction) >= 1 for instruction in instructions)
        assert len(instructions) >= 2
        assert all(
            not isinstance(instruction, Concatenated) for instruction in instructions
        )

        assert all(
            instruction.dtype == instructions[0].dtype for instruction in instructions
        )

        self._instructions = instructions

        # self._instruction_bounds[i] is the first element index (included) the i-th
        # instruction
        #
        # self._instruction_bounds[i+1] is the last element index (excluded) of the
        # i-th instruction
        self._instruction_bounds = (0,) + tuple(
            itertools.accumulate(len(instruction) for instruction in self._instructions)
        )
        self._length = Length(self._instruction_bounds[-1])

    def __repr__(self):
        inner = ", ".join(repr(instruction) for instruction in self._instructions)
        return f"Concatenated({inner})"

    def __str__(self):
        sub_strings = [str(instruction) for instruction in self._instructions]
        return " + ".join(sub_strings)

    @overload
    def __getitem__(self, item: int) -> T: ...

    @overload
    def __getitem__(self, item: slice) -> SequencerInstruction[T]: ...

    @overload
    def __getitem__[S: np.generic](self, item: str) -> SequencerInstruction[S]: ...

    def __getitem__(self, item):
        match item:
            case int() as index:
                return self._get_index(index)
            case slice() as slice_:
                return self._get_slice(slice_)
            case str() as field:
                return self._get_field(field)
            case _:
                assert_never(item)

    def _get_index(self, index: int) -> T:
        index = _normalize_index(index, len(self))
        instruction_index = bisect.bisect_right(self._instruction_bounds, index) - 1
        instruction = self._instructions[instruction_index]
        instruction_start_index = self._instruction_bounds[instruction_index]
        return instruction[index - instruction_start_index]

    def _get_slice(self, slice_: slice) -> SequencerInstruction[T]:
        start, stop, step = _normalize_slice(slice_, len(self))
        if step != 1:
            raise NotImplementedError
        start_step_index = bisect.bisect_right(self._instruction_bounds, start) - 1
        stop_step_index = bisect.bisect_left(self._instruction_bounds, stop) - 1

        results: list[SequencerInstruction[T]] = [empty_like(self)]
        for instruction_index in range(start_step_index, stop_step_index + 1):
            instruction_start_index = self._instruction_bounds[instruction_index]
            instruction_slice_start = max(start, instruction_start_index)
            instruction_stop_index = self._instruction_bounds[instruction_index + 1]
            instruction_slice_stop = min(stop, instruction_stop_index)
            instruction_slice = slice(
                instruction_slice_start - instruction_start_index,
                instruction_slice_stop - instruction_start_index,
                step,
            )
            results.append(self._instructions[instruction_index][instruction_slice])
        return concatenate(*results)

    def _get_field(self, field: str) -> SequencerInstruction:
        return Concatenated(*(instruction[field] for instruction in self._instructions))

    @property
    def dtype(self) -> numpy.dtype[T]:
        return self._instructions[0].dtype

    def as_type[S: np.generic](self, dtype: numpy.dtype[S]) -> Concatenated[S]:
        return Concatenated[S](
            *(instruction.as_type(dtype) for instruction in self._instructions)
        )

    def __len__(self) -> Length:
        return self._length

    @property
    def depth(self) -> Depth:
        return Depth(max(instruction.depth for instruction in self._instructions) + 1)

    def to_pattern(self) -> Pattern[T]:
        # noinspection PyProtectedMember
        new_array = numpy.concatenate(
            [instruction.to_pattern()._pattern for instruction in self._instructions],
            casting="safe",
        )
        return Pattern.create_without_copy(new_array)

    def __eq__(self, other):
        if isinstance(other, Concatenated):
            return self._instructions == other._instructions
        else:
            return NotImplemented

    def apply[
        S: np.generic
    ](self, func: Callable[[Array1D[T]], Array1D[S]]) -> Concatenated[S]:
        return Concatenated(
            *(instruction.apply(func) for instruction in self._instructions)
        )


class Repeated[T: np.generic](SequencerInstruction[T]):
    """Represents a repetition of an instruction.

    Use the `*` operator with an integer to repeat an instruction.
    Do not use the class constructor directly.

    Attributes:
        instruction: The instruction to repeat.
        repetitions: The number of times to repeat the instruction.
    """

    __slots__ = ("_repetitions", "_instruction", "_length")

    @property
    def repetitions(self) -> int:
        return self._repetitions

    @property
    def instruction(self) -> SequencerInstruction[T]:
        return self._instruction

    def __init__(self, repetitions: int, instruction: SequencerInstruction[T]):
        """
        Do not use this constructor in user code.
        Instead, use the `*` operator.
        """

        assert isinstance(repetitions, int)
        assert isinstance(instruction, SequencerInstruction)
        assert repetitions >= 2
        assert len(instruction) >= 1
        assert not isinstance(instruction, Repeated)

        self._repetitions = repetitions
        self._instruction = instruction
        self._length = Length(len(self._instruction) * self._repetitions)

    def __repr__(self):
        return (
            f"Repeated(repetitions={self._repetitions!r},"
            f" instruction={self._instruction!r})"
        )

    def __str__(self):
        if isinstance(self._instruction, Concatenated):
            return f"{self._repetitions} * ({self._instruction!s})"
        else:
            return f"{self._repetitions} * {self._instruction!s}"

    def __len__(self) -> Length:
        return self._length

    @overload
    def __getitem__(self, item: int) -> T: ...

    @overload
    def __getitem__(self, item: slice) -> SequencerInstruction[T]: ...

    @overload
    def __getitem__[S: np.generic](self, item: str) -> SequencerInstruction[S]: ...

    def __getitem__(self, item):
        if isinstance(item, int):
            return self._get_index(item)
        elif isinstance(item, slice):
            return self._get_slice(item)
        elif isinstance(item, str):
            return self._get_field(item)
        else:
            assert_never(item)

    def _get_index(self, index: int) -> T:
        index = _normalize_index(index, len(self))
        _, r = divmod(index, len(self._instruction))
        return self._instruction[r]

    def _get_slice(self, slice_: slice) -> SequencerInstruction[T]:
        start, stop, step = _normalize_slice(slice_, len(self))
        if step != 1:
            raise NotImplementedError
        length = len(self._instruction)
        first_repetition = math.ceil(start / length)
        last_repetition = math.floor(stop / length)
        if first_repetition > last_repetition:
            return self._instruction[
                start - first_repetition * length : stop - first_repetition * length
            ]
        else:
            previous_repetition = math.floor(start / length)
            prepend = self._instruction[
                start
                - previous_repetition
                * length : (first_repetition - previous_repetition)
                * length
            ]
            middle = self._instruction * (last_repetition - first_repetition)
            append = self._instruction[: stop - last_repetition * length]
            return prepend + middle + append

    def _get_field(self, field: str) -> SequencerInstruction:
        return Repeated(self._repetitions, self._instruction[field])

    @property
    def dtype(self) -> numpy.dtype[T]:
        return self._instruction.dtype

    def as_type[S: np.generic](self, dtype: numpy.dtype[S]) -> Repeated[S]:
        return Repeated(self._repetitions, self._instruction.as_type(dtype))

    @property
    def depth(self) -> Depth:
        return Depth(self._instruction.depth + 1)

    def to_pattern(self) -> Pattern[T]:
        inner_pattern = self._instruction.to_pattern()
        # noinspection PyProtectedMember
        new_array = numpy.tile(inner_pattern._pattern, self._repetitions)
        return Pattern.create_without_copy(new_array)

    def __eq__(self, other):
        if isinstance(other, Repeated):
            return (
                self._repetitions == other._repetitions
                and self._instruction == other._instruction
            )
        else:
            return NotImplemented

    def apply[
        S: np.generic
    ](self, func: Callable[[Array1D[T]], Array1D[S]]) -> Repeated[S]:
        return Repeated(self._repetitions, self._instruction.apply(func))


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


def empty_like[T: np.generic](instruction: SequencerInstruction[T]) -> Pattern[T]:
    return empty_with_dtype(instruction.dtype)


def empty_with_dtype[T: np.generic](dtype: numpy.dtype[T]) -> Pattern[T]:
    return Pattern([], dtype=dtype)


def concatenate[
    T: np.generic
](*instructions: SequencerInstruction[T]) -> SequencerInstruction[T]:
    """Concatenates the given instructions into a single instruction.

    If not all instructions have the same dtype, the result will have the dtype that
    can hold all the values of the instructions.

    Raises:
        ValueError: If there is not at least one instruction provided.
    """

    if len(instructions) == 0:
        raise ValueError("Must provide at least one instruction")
    if not all(
        isinstance(instruction, SequencerInstruction) for instruction in instructions
    ):
        raise TypeError("All instructions must be instances of SequencerInstruction")
    dtype = instructions[0].dtype
    if not all(instruction.dtype == dtype for instruction in instructions):
        result_dtype = np.result_type(
            *[instruction.dtype for instruction in instructions]
        )
        instructions = tuple(
            instruction.as_type(result_dtype) for instruction in instructions
        )
    return _concatenate(*instructions)


def _concatenate[
    T: np.generic
](*instructions: SequencerInstruction[T]) -> SequencerInstruction[T]:
    assert len(instructions) >= 1
    assert all(
        instruction.dtype == instructions[0].dtype for instruction in instructions
    )

    instruction_deque = collections.deque[SequencerInstruction[T]](
        _break_concatenations(instructions)
    )

    useful_instructions: list[SequencerInstruction[T]] = []
    while instruction_deque:
        instruction = instruction_deque.popleft()
        if len(instruction) == 0:
            continue
        if isinstance(instruction, Pattern):
            concatenated_patterns: list[Pattern[T]] = [instruction]
            while instruction_deque and isinstance(instruction_deque[0], Pattern):
                pattern = instruction_deque.popleft()
                assert isinstance(pattern, Pattern)
                concatenated_patterns.append(pattern)
            if len(concatenated_patterns) == 1:
                useful_instructions.append(concatenated_patterns[0])
            else:
                useful_instructions.append(
                    Pattern(
                        numpy.concatenate(
                            [pattern.array for pattern in concatenated_patterns],
                            casting="safe",
                        )
                    )
                )
        else:
            useful_instructions.append(instruction)

    if len(useful_instructions) == 0:
        return empty_like(instructions[0])
    elif len(useful_instructions) == 1:
        return useful_instructions[0]
    else:
        return Concatenated(*useful_instructions)


def _break_concatenations[
    T: np.generic
](instructions: Sequence[SequencerInstruction[T]],) -> list[SequencerInstruction[T]]:
    flat: list[SequencerInstruction[T]] = []
    for instruction in instructions:
        if isinstance(instruction, Concatenated):
            flat.extend(instruction.instructions)
        else:
            flat.append(instruction)
    return flat
