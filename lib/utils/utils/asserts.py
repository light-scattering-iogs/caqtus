"""Defines utility functions for assertions.

All functions defined in this module are only active when __debug__ is True, i.e. when
the program is run in debug mode.
When not in debug mode, the functions are no-ops.
"""

from collections.abc import Callable, MutableSequence
from typing import Concatenate, TypeVar, ParamSpec

T = TypeVar("T")
P = ParamSpec("P")
S = TypeVar("S", bound=MutableSequence)


def assert_length_changed(
    difference: int,
) -> Callable[[Callable[Concatenate[S, P], T]], Callable[Concatenate[S, P], T]]:
    """Decorator for functions that change the length of a sequence.

    The first argument of the function must be a mutable sequence.
    If the length of the sequence does not change by the expected amount, an
    AssertionError is raised.

    Args:
        difference: The expected difference in length before and after the function is
        called.
    """

    def decorator(
        fun: Callable[Concatenate[S, P], T]
    ) -> Callable[Concatenate[S, P], T]:
        if __debug__:

            def wrapper(self, *args, **kwargs):
                length_before = len(self)
                result = fun(self, *args, **kwargs)
                length_after = len(self)
                assert length_after == length_before + difference
                return result

            return wrapper
        else:
            return fun

    return decorator
