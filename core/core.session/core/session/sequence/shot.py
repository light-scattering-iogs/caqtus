from __future__ import annotations

import typing

# We don't do these imports at runtime because it would create a circular import.
if typing.TYPE_CHECKING:
    from .sequence import Sequence


class Shot:
    """Gives access to the data of a shot."""

    def __init__(self, sequence: Sequence, index: int):
        self._sequence = sequence
        self._index = index

    @property
    def sequence(self) -> "Sequence":
        """The sequence to which this shot belongs."""

        return self._sequence

    @property
    def index(self) -> int:
        """The index of this shot in the sequence."""

        return self._index

    def __repr__(self):
        return f"Shot(sequence={self._sequence!r}, index={self._index})"

    def __eq__(self, other):
        return (
            isinstance(other, Shot)
            and self.sequence == other.sequence
            and self.index == other.index
        )

    def __hash__(self):
        return hash((self.sequence, self.index))
