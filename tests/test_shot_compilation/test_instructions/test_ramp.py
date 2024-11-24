from typing import assert_type

import numpy as np

from caqtus.instructions import ramp, Empty, Ramp, Pattern


def test_ramp_creation():
    r = ramp(0, 1, 5)
    assert not isinstance(r, Empty | Pattern)
    assert r.dtype() == np.dtype(np.float64)
    assert_type(r, Ramp)
