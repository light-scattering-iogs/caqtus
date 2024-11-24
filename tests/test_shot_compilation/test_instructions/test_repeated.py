from typing import assert_type

import numpy as np
from typing_extensions import reveal_type, TypeVar

from caqtus.instructions import pattern, Repeated, Pattern, Empty
from caqtus.instructions._indexing import SupportsSlicing
from caqtus.instructions._repeated import (
    SelfAddable,
    CanAddMultiplicationWithSlice,
    SupportsRepeatedSlicing,
)
from caqtus.instructions._typing import SubInstruction, Addable, Multipliable


def test_repeated_creation():
    p = pattern([1, 2, 3])
    assert not isinstance(p, Empty)
    r = Repeated(5, p)

    assert r.dtype() == p.dtype()
    assert_type(r, Repeated[Pattern[np.int64]])


def test_repeated_slice():
    p = pattern([1, 2, 3])
    assert not isinstance(p, Empty)

    r = Repeated(5, p)
    reveal_type(r)
    r._get_slice(slice(1, 3))

    a: Pattern[np.int64] = ...

    SliceR = TypeVar(
        "SliceR", bound=SubInstruction, covariant=True, default=SubInstruction
    )

    def f[SliceR: SubInstruction](x: SupportsRepeatedSlicing[SliceR]) -> SliceR:
        raise NotImplementedError

    reveal_type(f(a))

    def g(x: SelfAddable[CanAddMultiplicationWithSlice[SubInstruction, SliceR]]):
        pass

    reveal_type(g(a))

    def h(x: CanAddMultiplicationWithSlice[SubInstruction, SliceR]):
        pass

    reveal_type(h(a))
