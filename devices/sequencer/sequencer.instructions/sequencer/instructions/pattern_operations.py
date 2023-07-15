from abc import ABC
from typing import Protocol, TypeVar, overload, SupportsInt, Generic, Sized

_T = TypeVar("_T")


class Pattern(Sized, Protocol[_T]):
    @overload
    def __getitem__(self, index: SupportsInt) -> _T:
        ...

    @overload
    def __getitem__(self, index: slice) -> "Pattern[_T]":
        ...

    def __getitem__(self, index):
        ...


PatternType = TypeVar("PatternType", bound=Pattern)


class Operation(Sized, ABC, Generic[PatternType]):
    pass


class Add(Operation[PatternType]):
    def __init__(
        self, first_operand: Operation[PatternType], second_part: Operation[PatternType]
    ):
        self._first_part = first_operand
        self._second_part = second_part

    def __len__(self) -> int:
        return len(self._first_part) + len(self._second_part)

    def __getitem__(self, index: SupportsInt) -> PatternType:
        return self.pattern[index] + self.value
