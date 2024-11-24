from typing import assert_type

import numpy as np

from caqtus.instructions import pattern, Pattern, Empty


def test_bool_pattern():
    p = pattern([True, False, True])
    assert not isinstance(p, Empty)
    assert p.dtype() == np.dtype(np.bool)
    assert_type(p, Pattern[np.bool])


def test_int_pattern():
    p = pattern([1, 2, 3])
    assert not isinstance(p, Empty)
    assert p.dtype() == np.dtype(np.int64)
    assert_type(p, Pattern[np.int64])


def test_float_pattern():
    p = pattern([1.0, 2.0, 3.0])
    assert not isinstance(p, Empty)
    assert p.dtype() == np.dtype(np.float64)
    assert_type(p, Pattern[np.float64])


def test_mixed_int_float_pattern():
    p = pattern([1, 2.0, 3])
    assert not isinstance(p, Empty)
    assert p.dtype() == np.dtype(np.float64)
    assert_type(p, Pattern[np.float64])


def test_get_index():
    p = pattern([1, 2, 3])
    assert not isinstance(p, Empty)
    assert p[0] == 1


def test_get_slice():
    p = pattern([1, 2, 3])
    assert not isinstance(p, Empty)
    assert p[1:3] == pattern([2, 3])


def test_get_empty_slice():
    p = pattern([1, 2, 3])
    assert not isinstance(p, Empty)
    assert p[1:1] == Empty()
