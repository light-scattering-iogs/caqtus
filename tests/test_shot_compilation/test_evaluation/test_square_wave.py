import pytest

from caqtus.shot_compilation._evaluation._time_dependent_expression._digital_expression import (
    square_wave,
)
from caqtus.shot_compilation.timed_instructions import create_ramp, Pattern
from caqtus.types.recoverable_exceptions import InvalidValueError


def test_ramp_less_than_one_period():
    r = create_ramp(0, 1, 100)
    assert square_wave(r, 0.5) == Pattern([True]) * 50 + Pattern([False]) * 50


def test_many_rep():
    r = create_ramp(0, 10, 1000)
    assert square_wave(r, 0.5) == (Pattern([True]) * 50 + Pattern([False]) * 50) * 10


def test_fail_on_too_fast_ramp():
    r = create_ramp(0, 1000, 10)
    with pytest.raises(InvalidValueError):
        square_wave(r, 0.5)


def test_duty_cycle():
    r = create_ramp(0, 10, 1000)
    assert square_wave(r, 0.1) == (Pattern([True]) * 10 + Pattern([False]) * 90) * 10
