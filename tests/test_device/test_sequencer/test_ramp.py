import pytest

from caqtus.device.sequencer.instructions import Ramp


def test():
    ramp = Ramp(0, 1, 5)
    assert ramp[0] == 0
    assert ramp[1] == 0.2
    assert ramp[2] == 0.4
    assert ramp[3] == 0.6
    assert ramp[4] == 0.8
    with pytest.raises(IndexError):
        assert ramp[5] == 1
