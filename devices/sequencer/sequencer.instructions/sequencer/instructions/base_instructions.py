import itertools
import logging
from abc import ABC, abstractmethod
from functools import cached_property
from math import floor, ceil
from typing import TypeVar, Protocol, runtime_checkable, overload, Iterator, Generic

from attr import frozen, field

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

T = TypeVar("T", covariant=True)


class SequenceInstruction(ABC, Generic[T]):
    """Interface defining a compact representation of a sequence of values.

    Instances of this class are a higher level representation of a sequence of values
    than bare arrays. They are easier to manipulate and can be stored more efficiently.
    Instead of storing all the values explicitly, they instead store the instructions to
    generate the sequence.

    For instance Pattern([1, 2, 3]) * 10_000_000 + Pattern([4, 5]) * 10_000_000,
    represents a sequence of 50 million values, but has a very small memory footprint
    since we only store the number of repetitions and the values to repeat instead of
    each value explicitly.

    Instances of this class are immutable. They can be concatenated with the `+`
    operator and repeated an integer number of times with the `*` operator. They can be
    subscripted with an integer or a slice.
    """

    @abstractmethod
    def __len__(self) -> int:
        """Return the length of the sequence represented by this instruction."""

        raise NotImplementedError()

    @abstractmethod
    def __iter__(self) -> Iterator[T]:
        """Return an iterator over the explicit values represented by this instruction.

        This is mostly useful for debugging purposes as it transforms an implicit
        representation into an explicit one, thus losing all potential performance
        benefits.
        """

        raise NotImplementedError()

    @overload
    def __getitem__(self, index: int) -> T:
        ...

    @overload
    def __getitem__(self, index: slice) -> "SequenceInstruction[T]":
        ...

    @abstractmethod
    def __getitem__(self, index):
        raise NotImplementedError()

    def __add__(self, other) -> "SequenceInstruction[T]":
        if isinstance(other, SequenceInstruction):
            if len(other) == 0:
                return self
            elif len(self) == 0:
                return other
            else:
                return Add(self, other)
        else:
            return NotImplemented

    def __mul__(self, other) -> "SequenceInstruction[T]":
        if isinstance(other, int):
            if other == 0:
                return self[:0]
            elif other == 1:
                return self
            else:
                if len(self) == 0:
                    return self
                else:
                    return Multiply(other, self)
        else:
            return NotImplemented

    def __rmul__(self, other) -> "SequenceInstruction[T]":
        return self.__mul__(other)

    @classmethod
    def empty_like(
        cls, instruction: "SequenceInstruction[T]"
    ) -> "SequenceInstruction[T]":
        return instruction[:0]


@runtime_checkable
class InternalPattern(Protocol[T]):
    def __len__(self) -> int:
        raise NotImplementedError()

    def __iter__(self) -> Iterator[T]:
        raise NotImplementedError()

    @overload
    def __getitem__(self, index: int) -> T:
        ...

    @overload
    def __getitem__(self, index: slice) -> "InternalPattern[T]":
        ...

    def __getitem__(self, index):
        raise NotImplementedError()


@frozen
class Pattern(SequenceInstruction[T]):
    """Explicit representation of a sequence of values.

    This is the most specific way to represent a sequence of values, by specifying them
    explicitly. It is also the most verbose and memory expensive way to represent the
    values.

    Fields:
        pattern: The sequence of values wrapped by this instruction. This must be a
        sequence of values implementing the `__len__` and `__getitem__` methods, like
        for example a list or a numpy array.
    """

    pattern: InternalPattern[T]

    def __len__(self) -> int:
        return len(self.pattern)

    def __getitem__(self, index):
        if isinstance(index, int):
            return self.pattern[index]
        elif isinstance(index, slice):
            return Pattern(self.pattern[index])
        else:
            raise TypeError("Index must be int or slice.")

    def __iter__(self):
        return iter(self.pattern)


@frozen
class Add(SequenceInstruction[T]):
    """Represent the concatenation of two sequences.

    Instances of this class are pure concatenations of two sequences: the left and right
    part cannot be empty.
    """

    left: SequenceInstruction[T] = field()
    right: SequenceInstruction[T] = field()

    # noinspection PyUnresolvedReferences
    @left.validator
    def _validate_left(self, _, value):
        if len(value) == 0:
            raise ValueError("Left instruction is empty.")

    # noinspection PyUnresolvedReferences
    @right.validator
    def _validate_right(self, _, value):
        if len(value) == 0:
            raise ValueError("Right instruction is empty.")

    def __len__(self) -> int:
        return self._length

    def __iter__(self):
        return itertools.chain(self.left, self.right)

    @cached_property
    def _length(self):
        return len(self.left) + len(self.right)

    def __getitem__(self, index):
        if isinstance(index, int):
            index = _normalize_integer_index(index, len(self))
            if index < len(self.left):
                return self.left[index]
            else:
                return self.right[index - len(self.left)]
        elif isinstance(index, slice):
            start, stop, step = _normalize_slice(index, len(self))
            if step != 1:
                raise ValueError("Step must be 1.")
            if start < len(self.left):
                if stop <= len(self.left):
                    return self.left[start:stop]
                else:
                    return self.left[start:] + self.right[: stop - len(self.left)]
            else:
                return self.right[start - len(self.left) : stop - len(self.left)]


@frozen
class Multiply(SequenceInstruction[T]):
    """Represent the repetition of a sequence of values.

    This allows to repeat a sequence of value a large number of times without having to
    store the sequence explicitly.

    Instances of this class are pure repetitions of a sequence: the repeated sequence
    cannot be empty and the number of repetitions must be strictly greater than 1.
    """

    repetitions: int = field()
    instruction: SequenceInstruction[T] = field()

    # noinspection PyUnresolvedReferences
    @repetitions.validator
    def _validate_repetitions(self, _, value):
        if value <= 1:
            raise ValueError(
                f"Repetitions must be strictly greater than 1, got {value}."
            )

    # noinspection PyUnresolvedReferences
    @instruction.validator
    def _validate_instruction(self, _, value):
        if len(value) == 0:
            raise ValueError("Instruction is empty.")

    def __len__(self):
        return self._length

    @cached_property
    def _length(self):
        return self.repetitions * len(self.instruction)

    def __iter__(self):
        return itertools.chain.from_iterable(
            itertools.repeat(self.instruction, self.repetitions)
        )

    def __getitem__(self, index):
        if isinstance(index, int):
            index = _normalize_integer_index(index, len(self))
            return self.instruction[index % len(self.instruction)]
        elif isinstance(index, slice):
            start, stop, step = _normalize_slice(index, len(self))
            if step != 1:
                raise ValueError("Step must be 1.")
            if len(self.instruction) == 1:
                return self.instruction * (stop - start)

            before_instruction = floor(start / len(self.instruction))
            before_instruction_start = before_instruction * len(self.instruction)
            next_instruction = floor(stop / len(self.instruction))
            next_instruction_start = next_instruction * len(self.instruction)

            if before_instruction == next_instruction:
                return self.instruction[
                    start - before_instruction_start : stop - before_instruction_start
                ]
            else:
                first_whole_instruction = ceil(start / len(self.instruction))
                first_whole_instruction_start = first_whole_instruction * len(
                    self.instruction
                )
                last_whole_instruction = floor(stop / len(self.instruction))
                last_whole_instruction_stop = last_whole_instruction * len(
                    self.instruction
                )

                whole_repetitions = last_whole_instruction - first_whole_instruction

                if whole_repetitions < 0:
                    whole_repetitions = 0

                before = self.instruction[
                    start
                    - before_instruction_start : first_whole_instruction_start
                    - before_instruction_start
                ]
                middle = self.instruction * whole_repetitions

                after = self.instruction[
                    last_whole_instruction_stop
                    - next_instruction_start : stop
                    - next_instruction_start
                ]
                return before + middle + after
        else:
            raise TypeError("Index must be int or slice.")

    def __mul__(self, other):
        if isinstance(other, int):
            if other == 0:
                return SequenceInstruction.empty_like(self)
            elif other == 1:
                return self
            else:
                return Multiply(self.repetitions * other, self.instruction)
        else:
            return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)


def _normalize_integer_index(index: int, length: int) -> int:
    if index < 0:
        index += length
    return index


def _normalize_slice(index: slice, length: int) -> tuple[int, int, int]:
    if index.start is None:
        start = 0
    else:
        start = _normalize_integer_index(index.start, length)
    if index.stop is None:
        stop = length
    else:
        stop = _normalize_integer_index(index.stop, length)
    if index.step is None:
        step = 1
    else:
        step = index.step

    return start, stop, step
