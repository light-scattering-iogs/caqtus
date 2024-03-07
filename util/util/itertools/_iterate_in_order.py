from collections.abc import Iterable, Callable, Iterator
from typing import TypeVar, SupportsInt

T = TypeVar("T")


def iterate_in_order(
    iterable: Iterable[T], index: Callable[[T], SupportsInt]
) -> Iterator[T]:
    """Iterate over an iterable in order of the index of its elements.

    The indices returned by the index function must be unique and consecutive, starting from 0.

    This function can be useful when you need to process elements in a specific order even if they are generated in a
    random order.

    Raises:
        ValueError: if the index of an element is not unique or if there is a gap in the indices.
    """

    result = {}
    current_index = 0
    for value in iterable:
        value_index = int(index(value))
        if value_index in result:
            raise ValueError(f"Index {value_index} appears twice")
        else:
            result[value_index] = value
        if current_index in result:
            yield result.pop(current_index)
            current_index += 1
    while current_index in result:
        yield result.pop(current_index)
        current_index += 1
    if result:
        raise ValueError(f"No value corresponds to index {current_index}")
