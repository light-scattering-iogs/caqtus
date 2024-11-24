from typing import Self


class Empty:
    def __eq__(self, other):
        return isinstance(other, Empty)

    def __repr__(self) -> str:
        return "Empty()"

    def __add__[T](self, other: T) -> T:
        return other

    def __mul__(self, other: int) -> Self:
        return self

    def __rmul__(self, other: int) -> Self:
        return self
