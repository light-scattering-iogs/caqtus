from collections.abc import Iterable
from typing import TypeVar

T = TypeVar("T")


def first(iterable: Iterable[T]) -> T:
    """Returns the first value of an iterable.

    Raises:
        ValueError if the iterable is empty.
    """

    iterator = iter(iterable)
    try:
        return next(iterator)
    except StopIteration:
        raise ValueError("Iterable is empty")
