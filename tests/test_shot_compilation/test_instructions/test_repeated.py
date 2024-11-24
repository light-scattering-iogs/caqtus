from typing import assert_type

import numpy as np

from caqtus.instructions import pattern, Repeated, Pattern


def test_repeated_creation():
    p = pattern([1, 2, 3])
    r = Repeated(5, p)

    assert r.dtype() == p.dtype()
    assert_type(r, Repeated[Pattern[np.int64]])
