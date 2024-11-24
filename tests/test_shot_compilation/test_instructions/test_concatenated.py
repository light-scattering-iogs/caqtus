from typing import assert_type

import numpy as np

from caqtus.instructions import pattern, Concatenated, Pattern


def test_bool_concatenated():
    p1 = pattern([True, False, True])
    p2 = pattern([True, False])
    c = Concatenated(p1, p2)
    assert c.dtype() == np.dtype(np.bool)
    assert_type(c, Concatenated[Pattern[np.bool], Pattern[np.bool]])
