from __future__ import annotations

from typing import (
    SupportsInt,
    Callable,
    SupportsFloat,
    overload,
)

import numpy as np

from caqtus.utils._no_public_constructor import NoPublicConstructor
from ._instructions import (
    SequencerInstruction,
    _normalize_slice,
    empty_with_dtype,
    Depth,
    Pattern,
    Array1D,
    _normalize_index,
    Length,
    Repeated,
    empty_like,
)
from ._stack import stack, merge_dtypes


def create_ramp(
    start: SupportsFloat, stop: SupportsFloat, length: SupportsInt
) -> SequencerInstruction[np.float64]:
    """Create a linear ramp between two values.

    Args:
        start: The initial value of the ramp.
        stop: The final value of the ramp.
        length: The number of points in the ramp.
    """

    length = int(length)

    start = np.float64(start)
    stop = np.float64(stop)

    if not np.isfinite(start):
        raise ValueError("Start must be finite.")

    if not np.isfinite(stop):
        raise ValueError("Stop must be finite.")

    if length < 0:
        raise ValueError("Length must be non-negative.")
    elif length == 0:
        return empty_with_dtype(start.dtype)
    else:
        return Ramp._create(start, stop, length)


class Ramp[T: (np.floating, np.void)](
    SequencerInstruction[T], metaclass=NoPublicConstructor
):
    """Represents an instruction that linearly ramps between two values.

    At index `i`, this instruction takes the value
    `start + i * (stop - start) / length`.

    Use the :func:`ramp` function to create instances of this class and don't use the
    constructor directly.

    This class is generic over the data type of the ramp.
    Since a ramp only makes sense for floating point values, the type parameter is
    constrained to be a floating point type or a structured type with only floating
    point leaf fields.
    """

    __slots__ = ("_start", "_stop", "_length")

    def __init__(self, start: T, stop: T, length: int) -> None:
        # The constructor is private. Use the :func:`ramp` function to create instances
        # of this class.
        self._start: T = start
        self._stop: T = stop
        self._length = Length(length)

        assert isinstance(self._start, np.generic)
        assert isinstance(self._stop, np.generic)
        assert Ramp.is_valid_dtype(self._start.dtype)
        assert self._start.dtype == self._stop.dtype
        assert isinstance(length, int)
        assert self._length >= 1

    @classmethod
    def is_valid_dtype(cls, dtype: np.dtype) -> bool:
        """Indicates if the dtype is valid for the start and stop values of a ramp.

        Returns:
            True if the dtype is a floating point type or a structured type with only
            floating point leaf fields, False otherwise.
        """

        if np.issubdtype(dtype, np.floating):
            return True
        if np.issubdtype(dtype, np.void):
            assert dtype.fields is not None
            return all(
                cls.is_valid_dtype(sub_dtype) for sub_dtype, *_ in dtype.fields.values()
            )
        return False

    @property
    def start(self) -> T:
        """The initial value of the ramp."""

        return self._start

    @property
    def stop(self) -> T:
        """The final value of the ramp."""

        return self._stop

    @property
    def dtype(self) -> np.dtype[T]:
        return self._start.dtype

    def __len__(self) -> Length:
        return self._length

    def __repr__(self):
        return f"{type(self).__name__}({self._start}, {self._stop}, {self._length})"

    def __str__(self):
        return f"{self._start} -{self._length}-> {self._stop}"

    @overload
    def __getitem__(self, item: int) -> T: ...

    @overload
    def __getitem__(self, item: slice) -> SequencerInstruction[T]: ...

    @overload
    def __getitem__(self, item: str) -> Ramp: ...

    def __getitem__(self, item):
        if isinstance(item, int):
            return self._get_index(item)
        elif isinstance(item, slice):
            return self._get_slice(item)
        elif isinstance(item, str):
            return self._get_channel(item)

    def _get_index(self, index: int) -> T:
        index = _normalize_index(index, len(self))

        if np.issubdtype(self.dtype, np.void):
            assert isinstance(self._start, np.void)
            assert isinstance(self._stop, np.void)
            assert self.dtype.names is not None
            value = tuple(
                self._start[name]
                + index * (self._stop[name] - self._start[name]) / self._length
                for name in self.dtype.names
            )

            return np.void(  # pyright: ignore[reportCallIssue]
                value,
                dtype=self.dtype,  # pyright: ignore[reportArgumentType]
            )
        else:
            assert isinstance(self._start, np.floating)
            assert isinstance(self._stop, np.floating)
            return self._start + index * (self._stop - self._start) / self._length

    def _get_slice(self, slice_: slice) -> SequencerInstruction[T]:
        start_index, stop_index, step = _normalize_slice(slice_, len(self))
        if step != 1:
            raise NotImplementedError
        start_value = self._get_index(start_index)
        if stop_index == len(self):
            stop_value = self._stop
        else:
            stop_value = self._get_index(stop_index)
        length = stop_index - start_index
        if length == 0:
            return empty_like(self)
        else:
            return Ramp._create(start_value, stop_value, stop_index - start_index)

    def _get_channel(self, channel: str) -> SequencerInstruction:
        if not np.issubdtype(self.dtype, np.void):
            raise ValueError("Can't get field if dtype is not a structured type.")
        assert self.dtype.names is not None
        if channel not in self.dtype.names:
            raise ValueError(f"Channel {channel} not found in dtype {self.dtype}.")
        assert isinstance(self._start, np.void)
        assert isinstance(self._stop, np.void)
        start_value = self._start[channel]
        stop_value = self._stop[channel]
        return Ramp._create(start_value, stop_value, self._length)

    def as_type[S: np.generic](self, dtype: np.dtype[S]) -> SequencerInstruction[S]:
        start = self._start.astype(dtype)
        if not isinstance(start, (np.floating, np.void)):
            raise TypeError("Can only convert to floating point or structured type.")

        stop = self._stop.astype(dtype)
        if not isinstance(stop, (np.floating, np.void)):
            raise TypeError("Can only convert to floating point or structured type.")

        return Ramp._create(start, stop, self._length)

    @property
    def depth(self) -> Depth:
        return Depth(1)

    def to_pattern(self) -> Pattern[T]:
        if np.issubdtype(self.dtype, np.void):
            assert self.dtype.names is not None
            assert isinstance(self._start, np.void)
            assert isinstance(self._stop, np.void)
            values = np.empty(len(self), dtype=self.dtype)
            for name in self.dtype.names:
                values[name] = np.linspace(
                    self._start[name], self._stop[name], len(self), endpoint=False
                )
            return Pattern.create_without_copy(values)
        else:
            assert isinstance(self._start, np.floating)
            assert isinstance(self._stop, np.floating)
            values = np.linspace(self._start, self._stop, self._length, endpoint=False)
            return Pattern.create_without_copy(values)

    def __eq__(self, other):
        if not isinstance(other, Ramp):
            return NotImplemented
        return (
            np.all(self._start == other._start)
            and np.all(self._stop == other._stop)
            and self._length == other._length
        )

    def apply[
        S: np.generic
    ](self, func: Callable[[Array1D[T]], Array1D[S]]) -> SequencerInstruction[S]:
        """Map a function element-wise to the ramp.

        Warning:
            Since an arbitrary function will not necessarily preserve linear ramps, the
            ramp is explicitly computed before applying the function.
            This may lead to poor performance and large memory usage for long ramps.
        """

        return self.to_pattern().apply(func)


@stack.register(Ramp, Ramp)
def _stack_ramps(a: Ramp, b: Ramp) -> SequencerInstruction:
    assert len(a) == len(b)

    start = _merge_values(a._start, b._start)
    stop = _merge_values(a._stop, b._stop)
    return Ramp._create(start, stop, len(a))


@stack.register(Ramp, Repeated)
def _stack_ramp_repeated(a: Ramp, b: Repeated) -> SequencerInstruction:
    if len(b.instruction) == 1:
        value = b.instruction[0]
        if not Ramp.is_valid_dtype(value.dtype):
            raise TypeError(
                f"Can't stack a ramp with an instruction having dtype {value.dtype}."
            )
        start = _merge_values(a.start, value)
        stop = _merge_values(a.stop, value)
        return Ramp._create(start, stop, len(a))
    else:
        return stack(a.to_pattern(), b.to_pattern())


@stack.register(Repeated, Ramp)
def _stack_repeated_ramp(a: Repeated, b: Ramp) -> SequencerInstruction:
    assert len(a) == len(b)

    if len(a.instruction) == 1:
        value = a.instruction[0]
        if not Ramp.is_valid_dtype(value.dtype):
            raise TypeError(
                f"Can't stack a ramp with an instruction having dtype {value.dtype}."
            )
        start = _merge_values(value, b.start)
        stop = _merge_values(value, b.stop)
        return Ramp._create(start, stop, len(b))
    else:
        return stack(a.to_pattern(), b.to_pattern())


def _merge_values(a: np.void, b: np.void) -> np.void:
    merged_dtype = merge_dtypes(a.dtype, b.dtype)
    assert a.dtype.names is not None
    assert b.dtype.names is not None
    return np.void(
        tuple(a[name] for name in a.dtype.names)
        + tuple(b[name] for name in b.dtype.names),
        dtype=merged_dtype,
    )
