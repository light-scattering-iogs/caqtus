import logging
from abc import ABC
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
        return len(self.left) + len(self.right)

    def __getitem__(self, index):
        if isinstance(index, int):
            while index < 0:
                index += len(self)
            if index < len(self.left):
                return self.left[index]
            else:
                return self.right[index - len(self.left)]
        elif isinstance(index, slice):
            if index.start is None:
                start = 0
            else:
                start = index.start
            if index.stop is None:
                stop = len(self)
            else:
                stop = index.stop
            if index.step is None:
                step = 1
            else:
                step = index.step
            if step != 1:
                raise ValueError("Step must be 1.")
            while start < 0:
                start += len(self)
            while stop < 0:
                stop += len(self)
            if start < len(self.left):
                if stop <= len(self.left):
                    return self.left[start:stop]
                else:
                    return self.left[start:] + self.right[: stop - len(self.left)]
            else:
                return self.right[start - len(self.left) : stop - len(self.left)]
