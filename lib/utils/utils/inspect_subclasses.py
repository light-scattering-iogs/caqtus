import inspect
import itertools
from typing import TypeVar, Iterator

_T = TypeVar("_T")


def get_subclasses(cls: type[_T]) -> Iterator[type[_T]]:
    """Get all the subclasses of a class.

    This returns the subclasses of a class, and the subclasses of those subclasses,
    etc. It only returns strict subclasses, not the class itself.
    """

    subclasses = cls.__subclasses__()

    return itertools.chain(
        subclasses,
        itertools.chain.from_iterable(
            get_subclasses(subclass) for subclass in subclasses
        ),
    )


def get_concrete_subclasses(cls: type[_T]) -> Iterator[type[_T]]:
    """Get all the concrete subclasses of a class.

    This returns the subclasses of a class, and the subclasses of those subclasses,
    etc. It only returns strict subclasses, not the class itself.

    A concrete subclass is a subclass that is not abstract.
    """

    return (
        subclass for subclass in get_subclasses(cls) if not inspect.isabstract(subclass)
    )
