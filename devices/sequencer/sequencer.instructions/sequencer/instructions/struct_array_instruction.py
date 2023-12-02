from __future__ import annotations

import abc
from typing import NewType, TypeVar, Generic, overload, Optional, assert_never, Self

import numpy
from numpy.typing import DTypeLike

Length = NewType("Length", int)
Width = NewType("Width", int)
Depth = NewType("Depth", int)

_T = TypeVar("_T")


class SequencerInstruction(abc.ABC, Generic[_T]):
    """An immutable representation of instructions to output on a sequencer.

    This represents a high-level series of instructions to output on a sequencer. Each instruction is a compact
    representation of values to output at integer time steps. The length of the instruction is the number of time steps
    it takes to output all the values. The width of the instruction is the number of channels that are output at each
    time step.
    """

    @overload
    def __getitem__(self, item: int) -> _T:
        ...

    @overload
    def __getitem__(self, item: slice) -> SequencerInstruction[_T]:
        ...

    @abc.abstractmethod
    def __getitem__(self, item: int | slice) -> _T | SequencerInstruction[_T]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def dtype(self) -> numpy.dtype:
        """Returns the dtype of the instruction."""

        raise NotImplementedError

    @abc.abstractmethod
    def as_type(self, dtype: numpy.dtype) -> SequencerInstruction:
        """Returns a new instruction with the given dtype."""

        raise NotImplementedError

    @abc.abstractmethod
    def __len__(self) -> Length:
        """Returns the length of the instruction in clock cycles."""

        raise NotImplementedError

    @property
    @abc.abstractmethod
    def width(self) -> Width:
        """Returns the number of parallel channels that are output at each time step."""

        raise NotImplementedError

    @property
    @abc.abstractmethod
    def depth(self) -> Depth:
        """Returns the number of nested instructions.

        The invariant `instruction.depth <= len(instruction)` always holds.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def to_pattern(self) -> Pattern:
        """Returns a flattened pattern of the instruction."""

        raise NotImplementedError

    @abc.abstractmethod
    def __eq__(self, other):
        raise NotImplementedError


class Pattern(SequencerInstruction):
    __slots__ = ("_pattern",)
    """An instruction to output a pattern on a sequencer."""

    def __init__(self, pattern, dtype: Optional[DTypeLike] = None):
        self._pattern = numpy.array(pattern, dtype=dtype)
        self._pattern.setflags(write=False)

    def __repr__(self):
        return f"Pattern(pattern={self._pattern!r})"

    def __str__(self):
        return str(self._pattern)

    def __getitem__(self, item):
        if isinstance(item, int):
            return self._pattern[item]
        elif isinstance(item, slice):
            # Here we don't create a new pattern through the constructor, because we want to avoid copying the
            # underlying numpy array. Instead, we create a new pattern and set its internal numpy array to a view of the
            # original pattern's array.
            new_pattern = object.__new__(type(self))
            new_pattern._pattern = self._pattern[
                item
            ]  # in numpy, slicing creates a view, so we don't copy here
            return new_pattern
        else:
            assert_never(item)

    @property
    def dtype(self) -> numpy.dtype:
        return self._pattern.dtype

    def as_type(self, dtype: numpy.dtype) -> Self:
        # Here we try to avoid copy if possible.
        new_pattern = object.__new__(type(self))
        new_pattern._pattern = self._pattern.astype(dtype, copy=False)
        return new_pattern

    def __len__(self) -> Length:
        return Length(len(self._pattern))

    @property
    def width(self) -> Width:
        fields = self.dtype.fields
        if fields is None:
            return Width(1)
        else:
            return Width(len(fields))

    @property
    def depth(self) -> Depth:
        return Depth(0)

    def to_pattern(self) -> Pattern:
        return self

    def __eq__(self, other):
        if isinstance(other, Pattern):
            return numpy.array_equal(self._pattern, other._pattern)
        else:
            return NotImplemented
