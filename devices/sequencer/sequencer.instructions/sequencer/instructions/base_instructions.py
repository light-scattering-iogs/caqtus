import logging
from abc import ABC, abstractmethod
from functools import cached_property
from math import floor, ceil
from typing import TypeVar, Protocol, runtime_checkable, overload, Iterator, Generic

from attr import frozen, field

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

T = TypeVar("T", covariant=True)


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


class Instruction(ABC, Generic[T]):
    @abstractmethod
    def __len__(self) -> int:
        raise NotImplementedError()

    def __iter__(self) -> Iterator[T]:
        return (self[i] for i in range(len(self)))

    @overload
    def __getitem__(self, index: int) -> T:
        ...

    @overload
    def __getitem__(self, index: slice) -> "Instruction[T]":
        ...

    @abstractmethod
    def __getitem__(self, index):
        raise NotImplementedError()

    def __add__(self, other) -> "Instruction[T]":
        if isinstance(other, Instruction):
            if len(other) == 0:
                return self
            elif len(self) == 0:
                return other
            else:
                return Add(self, other)
        else:
            return NotImplemented

    def __mul__(self, other) -> "Instruction[T]":
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

    def __rmul__(self, other) -> "Instruction[T]":
        return self.__mul__(other)


@frozen
class Pattern(Instruction[T]):
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
class Add(Instruction[T]):
    left: Instruction[T] = field()
    right: Instruction[T] = field()

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
class Multiply(Instruction[T]):
    repetitions: int = field()
    instruction: Instruction[T] = field()

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
                return empty_like(self)
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


def empty_like(instruction: Instruction[T]) -> Instruction[T]:
    return instruction[:0]
