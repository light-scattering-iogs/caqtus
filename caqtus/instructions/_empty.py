from typing import Literal


class Empty:
    def __eq__(self, other):
        return isinstance(other, Empty)

    def __len__(self) -> Literal[0]:
        return 0

    def __repr__(self) -> str:
        return "Empty()"

    def __add__[T](self, other: T) -> T:
        return other
