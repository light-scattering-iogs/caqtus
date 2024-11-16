from __future__ import annotations

import abc
import bisect
import heapq
import itertools
import math
from collections.abc import Sequence
from typing import (
    NewType,
    overload,
    Optional,
    assert_never,
    Callable,
    Any,
    Generic,
    Self,
)

import numpy
import numpy as np
import numpy.typing as npt
from typing_extensions import TypeIs, TypeVar

Length = NewType("Length", int)
Width = NewType("Width", int)
Depth = NewType("Depth", int)

S = TypeVar("S", bound=np.generic, covariant=True, default=np.generic)
T = TypeVar("T", bound=np.generic, covariant=True, default=np.generic)

InstrType = TypeVar("InstrType", bound=np.generic, covariant=True)
"""Represents the data type of the instruction."""


type Array1D[T: np.generic] = npt.NDArray[T]

type CombinedInstruction[LeafType: Leaf, T: np.generic] = (
    Leaf[LeafType, T] | Concatenated[LeafType, T] | Repeated[LeafType, T]
)
type TimedInstruction[LeafType: Leaf, T: np.generic] = CombinedInstruction[LeafType, T]


LT = TypeVar("LT", bound="Leaf", covariant=True)

IntGE2 = NewType("IntGE2", int)


class Empty(Generic[T]):
    """Represents an empty instruction."""

    def __init__(self, dtype: numpy.dtype[T]):
        self._dtype = dtype

    @property
    def dtype(self) -> numpy.dtype[T]:
        return self._dtype

    def __eq__(self, other):
        if isinstance(other, Empty):
            return self.dtype == other.dtype
        else:
            return NotImplemented

    @overload
    def __add__(
        self, other: CombinedInstruction[LT, T]
    ) -> CombinedInstruction[LT, T]: ...

    @overload
    def __add__(self, other: Empty[T]) -> Empty[T]: ...

    def __add__(
        self, other: CombinedInstruction[LT, T] | Empty[T]
    ) -> CombinedInstruction[LT, T] | Empty[T]:
        if is_empty(other):
            return self
        else:
            return other

    @overload
    def __radd__(
        self, other: CombinedInstruction[LT, T]
    ) -> CombinedInstruction[LT, T]: ...

    @overload
    def __radd__(self, other: Empty[T]) -> Empty[T]: ...

    def __radd__(
        self, other: CombinedInstruction[LT, T] | Empty[T]
    ) -> CombinedInstruction[LT, T] | Empty[T]:
        if is_empty(other):
            return self
        else:
            return other

    def __mul__(self, other: int) -> Self:
        return self

    def __rmul__(self, other: int) -> Self:
        return self

    @classmethod
    def like(cls, other: CombinedInstruction[Leaf, S] | Empty[S]) -> Empty[S]:
        return Empty(other.dtype)


class Leaf(Generic[LT, T], abc.ABC):
    @abc.abstractmethod
    def __len__(self) -> Length:
        """Returns the length of the instruction in clock cycles.

        This must be a strictly positive integer.
        """

        raise NotImplementedError

    @overload
    @abc.abstractmethod
    def __getitem__(self, item: int) -> T:
        """Returns the value at the given index."""

        ...

    @overload
    @abc.abstractmethod
    def __getitem__(self, item: slice) -> Leaf[LT, T] | Empty[T]:
        """Returns a sub-instruction over the given slice.

        Warning:
            Not all valid slices are supported.
            Only slices with a step of 1 are fully supported for all instructions.
        """

        ...

    @overload
    @abc.abstractmethod
    def __getitem__(self, item: str) -> Leaf[LT, np.generic]:
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
    def as_type(self, dtype: numpy.dtype[S]) -> Leaf[LT, S]:
        """Returns a new instruction with the given dtype."""

        raise NotImplementedError

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
    def merge(self, other: Leaf[LT, S]) -> Leaf[LT, np.void]:
        raise NotImplementedError

    @abc.abstractmethod
    def __eq__(self, other):
        raise NotImplementedError

    def __add__(
        self, other: CombinedInstruction[LT, T]
    ) -> Concatenated[LT, T] | Repeated[LT, T]:
        if is_combined_instruction(other):
            if isinstance(other, Leaf):
                if other == self:
                    return Repeated(IntGE2(2), self)
                else:
                    return Concatenated(self, other)
            elif isinstance(other, Concatenated):
                if other.instructions[0] == self:
                    front = 2 * self
                    assert not is_empty(front)
                    return Concatenated(front, *other.instructions[1:])
                else:
                    return Concatenated(self, *other.instructions)
            elif isinstance(other, Repeated):
                if other.instruction == self:
                    return Repeated(IntGE2(other.repetitions + 1), self)
                else:
                    return Concatenated(self, other)

        else:
            return NotImplemented

    def __mul__(self, other: int) -> Repeated[LT, T] | Empty[T] | Self:
        if other >= 2:
            return Repeated(IntGE2(other), self)
        elif other == 1:
            return self
        elif other == 0:
            return Empty.like(self)
        else:
            raise ValueError("Repetitions must be a positive integer")

    def __rmul__(self, other: int) -> Repeated[LT, T] | Empty[T] | Self:
        return self.__mul__(other)

    @property
    def width(self) -> Width:
        """Returns the number of parallel channels that are output at each time step."""

        fields = self.dtype.fields
        if fields is None:
            return Width(1)
        else:
            return Width(len(fields))

    def _repr_mimebundle_(self, include=None, exclude=None):
        from ._to_graph import to_graph

        graph = to_graph(self)
        return graph._repr_mimebundle_(include, exclude)


class Pattern[T: np.generic](Leaf["Pattern", T]):
    """An instruction representing a sequence of values.

    This is a fully explicit instruction for which each sample point must be given.

    Args:
        pattern: The sequence of values that this pattern represents.
        dtype: The dtype of the pattern.
            If not provided, it is inferred from the values.

    Raises:
        ValueError: If the pattern contains non-finite values.
    """

    # All values inside the pattern MUST be finite (no NaN, no inf).
    # This is ensured by public methods, but not necessarily by all private methods.

    __slots__ = ("_pattern", "_length")

    def __init__(self, pattern: npt.ArrayLike, dtype: Optional[np.dtype[T]] = None):
        self._pattern = numpy.array(pattern, dtype=dtype)
        if not _has_only_finite_values(self._pattern):
            raise ValueError("Pattern must contain only finite values")
        self._pattern.setflags(write=False)
        self._length = Length(len(self._pattern))
        assert self._is_canonical()

    def _is_canonical(self) -> bool:
        return self._length > 0

    def __repr__(self):
        if np.issubdtype(self.dtype, np.void):
            return f"Pattern({self._pattern.tolist()!r}, dtype={self.dtype})"
        else:
            return f"Pattern({self._pattern.tolist()!r})"

    def __str__(self):
        return str(self._pattern.tolist())

    @overload
    def __getitem__(self, item: int) -> T: ...

    @overload
    def __getitem__(self, item: slice) -> Pattern[T]: ...

    @overload
    def __getitem__(self, item: str) -> Pattern: ...

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
        if not _has_only_finite_values(array):
            raise ValueError("Pattern must contain only finite values")
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
        if not _has_only_finite_values(result):
            raise ValueError("Function must return an array with only finite values")
        return Pattern.create_without_copy(result)

    @property
    def array(self) -> Array1D[T]:
        return self._pattern


def _has_only_finite_values[T: np.generic](array: Array1D[T]) -> bool:
    if np.issubdtype(array.dtype, np.floating):
        return bool(np.all(np.isfinite(array)))
    else:
        return True


class Concatenated(Generic[LT, T]):
    """Represents an immutable concatenation of instructions.

    Use the `+` operator or the function :func:`concatenate` to concatenate
    instructions. Do not use the class constructor directly.
    """

    __slots__ = ("_instructions", "_instruction_bounds", "_length")
    __match_args__ = ("instructions",)

    @property
    def instructions(self) -> tuple[Leaf[LT, T] | Repeated[LT, T], ...]:
        """The instructions concatenated by this instruction."""

        return self._instructions

    def __init__(self, *instructions: Leaf[LT, T] | Repeated[LT, T]):
        assert len(instructions) >= 2
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

    def __repr__(self) -> str:
        inner = ", ".join(repr(instruction) for instruction in self._instructions)
        return f"Concatenated({inner})"

    def __str__(self) -> str:
        sub_strings = [str(instruction) for instruction in self._instructions]
        return " + ".join(sub_strings)

    @overload
    def __getitem__(self, item: int) -> T: ...

    @overload
    def __getitem__(self, item: slice) -> CombinedInstruction[LT, T] | Empty[T]: ...

    @overload
    def __getitem__(self, item: str) -> Concatenated[LT, np.generic]: ...

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

    def _get_slice(self, slice_: slice) -> CombinedInstruction[LT, T] | Empty[T]:
        start, stop, step = _normalize_slice(slice_, len(self))
        if step != 1:
            raise NotImplementedError
        start_step_index = bisect.bisect_right(self._instruction_bounds, start) - 1
        stop_step_index = bisect.bisect_left(self._instruction_bounds, stop) - 1

        results: list[CombinedInstruction[LT, T] | Empty[T]] = [empty_like(self)]
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

    def _get_field(self, field: str) -> Concatenated[LT, np.generic]:
        return Concatenated(*(instruction[field] for instruction in self._instructions))

    @property
    def dtype(self) -> numpy.dtype[T]:
        return self._instructions[0].dtype

    def as_type(self, dtype: numpy.dtype[S]) -> Concatenated[LT, S]:
        return Concatenated(
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

    def __add__(self, other: CombinedInstruction[LT, T]) -> Concatenated[LT, T]:
        if isinstance(other, Leaf):
            if other == self._instructions[-1]:
                end = 2 * other
                assert not is_empty(end)
                return Concatenated(*self._instructions[:-1], end)
            else:
                return Concatenated(*self._instructions, other)
        elif isinstance(other, Concatenated):
            if other.instructions[0] == self._instructions[-1]:
                middle = 2 * other.instructions[0]
                assert not is_empty(middle)
                return Concatenated(
                    *self._instructions[:-1],
                    middle,
                    *other.instructions[1:],
                )
            else:
                return Concatenated(*self._instructions, *other.instructions)
        elif isinstance(other, Repeated):
            if other.instruction == self._instructions[-1]:
                return Concatenated(
                    *self._instructions[:-1],
                    Repeated(IntGE2(other.repetitions + 1), other.instruction),
                )
            else:
                return Concatenated(*self._instructions, other)

    def __mul__(self, other: int) -> Repeated[LT, T] | Concatenated[LT, T] | Empty[T]:
        if other >= 2:
            return Repeated(IntGE2(other), self)
        elif other == 1:
            return self
        elif other == 0:
            return Empty.like(self)
        else:
            raise ValueError("Repetitions must be a positive integer")

    def __rmul__(self, other: int) -> Repeated[LT, T] | Concatenated[LT, T] | Empty[T]:
        return self.__mul__(other)

    def merge(
        self, other: CombinedInstruction[LT, S]
    ) -> CombinedInstruction[LT, np.void]:
        if len(self) != len(other):
            raise ValueError("Instructions must have the same length")
        if isinstance(other, Leaf):
            return self._merge_leaf(other)
        elif isinstance(other, Concatenated):
            return self._merge_concatenation(other)
        elif isinstance(other, Repeated):
            return self._merge_repeated(other)

    def _merge_leaf(self, other: Leaf[LT, S]) -> CombinedInstruction[LT, np.void]:
        results = []
        for self_part, (start, stop) in zip(
            self.instructions,
            itertools.pairwise(self._instruction_bounds),
            strict=True,
        ):
            other_part = other[start:stop]
            assert not is_empty(other_part)
            merged = self_part.merge(other_part)
            results.append(merged)
        return _concatenate(*results)

    def _merge_repeated(
        self, other: Repeated[LT, S]
    ) -> CombinedInstruction[LT, np.void]:
        results = []
        for self_part, (start, stop) in zip(
            self.instructions,
            itertools.pairwise(self._instruction_bounds),
            strict=True,
        ):
            other_part = other[start:stop]
            assert not is_empty(other_part)
            if isinstance(self_part, Leaf):
                merged = other_part.merge(self_part)
            else:
                merged = self_part.merge(other_part)
            results.append(merged)
        return _concatenate(*results)

    def _merge_concatenation(
        self, other: Concatenated[LT, S]
    ) -> CombinedInstruction[LT, np.void]:
        new_bounds = heapq.merge(self._instruction_bounds, other._instruction_bounds)
        results = []
        for start, stop in itertools.pairwise(new_bounds):
            self_part = self[start:stop]
            other_part = other[start:stop]
            if not is_empty(self_part):
                assert not is_empty(other_part)
                if isinstance(self_part, Leaf):
                    merged = other_part.merge(self_part)
                else:
                    merged = self_part.merge(other_part)
                results.append(merged)
        return _concatenate(*results)

    def _repr_mimebundle_(self, include=None, exclude=None):
        from ._to_graph import to_graph

        graph = to_graph(self)
        return graph._repr_mimebundle_(include, exclude)


class Repeated(Generic[LT, T]):
    """Represents a repetition of an instruction.

    Use the `*` operator with an integer to repeat an instruction.
    Do not use the class constructor directly.
    """

    __slots__ = ("_repetitions", "_instruction", "_length")

    @property
    def repetitions(self) -> IntGE2:
        """The number of times the instruction is repeated."""

        return self._repetitions

    @property
    def instruction(self) -> Leaf[LT, T] | Concatenated[LT, T]:
        """The instruction that is repeated."""

        return self._instruction

    def __init__(
        self, repetitions: IntGE2, instruction: Leaf[LT, T] | Concatenated[LT, T]
    ):
        """
        Do not use this constructor in user code.
        Instead, use the `*` operator.
        """

        assert isinstance(repetitions, int)
        assert repetitions >= 2
        assert len(instruction) >= 1
        assert not isinstance(instruction, Repeated)

        self._repetitions = repetitions
        self._instruction = instruction
        self._length = Length(len(self._instruction) * self._repetitions)

    def __repr__(self) -> str:
        return (
            f"Repeated(repetitions={self._repetitions!r},"
            f" instruction={self._instruction!r})"
        )

    def __str__(self) -> str:
        if isinstance(self._instruction, Concatenated):
            return f"{self._repetitions} * ({self._instruction!s})"
        else:
            return f"{self._repetitions} * {self._instruction!s}"

    def __len__(self) -> Length:
        return self._length

    @overload
    def __getitem__(self, item: int) -> T: ...

    @overload
    def __getitem__(self, item: slice) -> CombinedInstruction[LT, T] | Empty[T]: ...

    @overload
    def __getitem__(self, item: str) -> Repeated[LT, np.generic]: ...

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

    def _get_slice(self, slice_: slice) -> CombinedInstruction[LT, T] | Empty[T]:
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

    def _get_field(self, field: str) -> CombinedInstruction[LT, np.generic]:
        return Repeated(self._repetitions, self._instruction[field])

    @property
    def dtype(self) -> numpy.dtype[T]:
        return self._instruction.dtype

    def as_type(self, dtype: numpy.dtype[S]) -> Repeated[LT, S]:
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

    def __add__(self, other: CombinedInstruction[LT, T]) -> CombinedInstruction[LT, T]:
        if isinstance(other, Leaf):
            if other == self._instruction:
                return Repeated(IntGE2(self._repetitions + 1), self._instruction)
            else:
                return Concatenated(self, other)
        elif isinstance(other, Concatenated):
            if other.instructions[0] == self._instruction:
                return Concatenated(
                    Repeated(IntGE2(self._repetitions + 1), self._instruction),
                    *other.instructions[1:],
                )
            else:
                return Concatenated(self, *other.instructions)
        elif isinstance(other, Repeated):
            if other.instruction == self._instruction:
                return Repeated(
                    IntGE2(self._repetitions + other.repetitions), self._instruction
                )
            else:
                return Concatenated(self, other)

    def __mul__(self, other: int) -> Repeated[LT, T] | Empty[T]:
        if other >= 1:
            return Repeated(IntGE2(self._repetitions * other), self._instruction)
        elif other == 0:
            return Empty.like(self)
        else:
            raise ValueError("Repetitions must be a positive integer")

    def __rmul__(self, other: int) -> Repeated[LT, T] | Empty[T]:
        return self.__mul__(other)

    def _repr_mimebundle_(self, include=None, exclude=None):
        from ._to_graph import to_graph

        graph = to_graph(self)
        return graph._repr_mimebundle_(include, exclude)

    def merge(
        self, other: CombinedInstruction[LT, S]
    ) -> CombinedInstruction[LT, np.void]:
        if len(self) != len(other):
            raise ValueError("Instructions must have the same length")
        if isinstance(other, Leaf):
            return self._merge_leaf(other)
        elif isinstance(other, Concatenated):
            return self._merge_concatenation(other)
        elif isinstance(other, Repeated):
            return self._merge_repeated(other)

    def _merge_leaf(self, other: Leaf[LT, S]) -> CombinedInstruction[LT, np.void]:
        results = []
        for rep in range(self.repetitions):
            start = rep * len(self.instruction)
            stop = (rep + 1) * len(self.instruction)
            other_part = other[start:stop]
            assert not is_empty(other_part)
            if isinstance(self.instruction, Leaf):
                merged = other_part.merge(self.instruction)
            else:
                merged = self.instruction.merge(other_part)
            results.append(merged)
        return _concatenate(*results)

    def _merge_concatenation(
        self, other: Concatenated[LT, S]
    ) -> CombinedInstruction[LT, np.void]:
        return other.merge(self)

    def _merge_repeated(
        self, other: Repeated[LT, S]
    ) -> CombinedInstruction[LT, np.void]:
        lcm = math.lcm(len(self.instruction), len(other.instruction))
        if lcm == len(self):
            b_a = _concatenate(*[self.instruction] * self.repetitions)
            b_b = _concatenate(*[other.instruction] * other.repetitions)
        else:
            r_a = lcm // len(self.instruction)
            b_a = self.instruction * r_a
            r_b = lcm // len(other.instruction)
            b_b = other.instruction * r_b
        assert not is_empty(b_a)
        assert not is_empty(b_b)
        if isinstance(b_a, Leaf):
            block = b_b.merge(b_a)
        else:
            block = b_a.merge(b_b)
        result = block * (len(self) // len(block))
        assert not is_empty(result)
        return result


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


def empty_like[
    LT: Leaf, T: np.generic
](instruction: CombinedInstruction[LT, T]) -> Empty[T]:
    return empty_with_dtype(instruction.dtype)


def empty_with_dtype(dtype: numpy.dtype[T]) -> Empty[T]:
    return Empty(dtype)


def concatenate[
    LT: Leaf, T: np.generic
](*instructions: CombinedInstruction[LT, T] | Empty[T]) -> (
    CombinedInstruction[LT, T] | Empty[T]
):
    """Concatenates the given instructions into a single instruction.

    All instructions must have the same dtype.

    Raises:
        ValueError: If there is not at least one instruction provided.
    """

    if len(instructions) == 0:
        raise ValueError("Must provide at least one instruction")
    if not all(is_combined_instruction(instruction) for instruction in instructions):
        raise TypeError("All instructions must be instances of CombinedInstruction")
    dtype = instructions[0].dtype
    if not all(instruction.dtype == dtype for instruction in instructions):
        raise ValueError("All instructions must have the same dtype")
    non_empty_instructions = [
        instruction for instruction in instructions if not is_empty(instruction)
    ]
    if len(non_empty_instructions) == 0:
        return Empty.like(instructions[0])
    elif len(non_empty_instructions) == 1:
        return non_empty_instructions[0]
    else:
        return _concatenate(*non_empty_instructions)


def _concatenate[
    LT: Leaf, T: np.generic
](*instructions: CombinedInstruction[LT, T]) -> CombinedInstruction[LT, T]:
    assert len(instructions) >= 1
    assert all(
        instruction.dtype == instructions[0].dtype for instruction in instructions
    )

    useful_instructions = [
        instruction for instruction in _break_concatenations(instructions)
    ]

    assert len(useful_instructions) >= 1
    if len(useful_instructions) == 1:
        return useful_instructions[0]
    else:
        return Concatenated(*useful_instructions)


def _break_concatenations[
    LT: Leaf, T: np.generic
](
    instructions: Sequence[CombinedInstruction[LT, T]],
) -> list[
    Leaf[LT, T] | Repeated[LT, T]
]:
    flat = []
    for instruction in instructions:
        if isinstance(instruction, Concatenated):
            flat.extend(instruction.instructions)
        else:
            flat.append(instruction)
    return flat


def is_combined_instruction(instruction: Any) -> TypeIs[CombinedInstruction]:
    return isinstance(instruction, (Leaf, Concatenated, Repeated))


def is_empty(instruction: CombinedInstruction[Leaf, T] | Empty[T]) -> TypeIs[Empty[T]]:
    return isinstance(instruction, Empty)
