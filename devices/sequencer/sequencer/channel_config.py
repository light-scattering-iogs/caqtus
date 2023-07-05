from dataclasses import dataclass
from typing import TypeVar, Generic, get_args

from numpy.typing import DTypeLike

_T = TypeVar("_T", bound=DTypeLike)


@dataclass
class ChannelConfig(Generic[_T]):
    """Information about a channel in a time sequence.

    Even at runtime, the generic type of the channel must be specified because it allows to get the dtype of the arrays
    to instantiate.

    Fields:
        default_value: The default value of the channel. This is the value the channel will take if a value is not
            defined for it at a given time.
        initial_value: The value assumed to be taken by the channel before the sequence starts.
        final_value: The value assumed to be taken by the channel after the sequence ends.
    """

    default_value: _T
    initial_value: _T
    final_value: _T

    @property
    def dtype(self) -> type[_T]:
        """The numpy dtype of the channel."""

        generic_args = get_args(self.__orig_class__)
        if len(generic_args) != 1:
            raise TypeError(
                "ChannelConfig must be a generic type with a single argument (the"
                " dtype)"
            )
        return get_args(self.__orig_class__)[0]
