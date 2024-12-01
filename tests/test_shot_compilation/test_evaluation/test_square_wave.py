import pytest

from caqtus.shot_compilation._evaluation._time_dependent_expression._digital_expression import (
    square_wave,
    evaluate_time_dependent_digital_expression,
)
from caqtus.shot_compilation.timed_instructions import create_ramp, Pattern
from caqtus.shot_compilation.timing import to_time
from caqtus.types.expression import Expression
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


def test_initial_offset():
    r = create_ramp(0.1, 10.1, 1000)
    assert square_wave(r, 0.1) == (Pattern([False]) * 90 + Pattern([True]) * 10) * 10


def test_expression_evaluation():
    expr = Expression("square_wave(t * 1 kHz)")

    result = evaluate_time_dependent_digital_expression(
        expr, {}, to_time(0), to_time(1), to_time(1e-6)
    )
    assert result == (Pattern([True]) * 500 + Pattern([False]) * 500) * 1000


def test_square_wave_divided():
    expr = Expression("square_wave(t / 1 ms)")

    result = evaluate_time_dependent_digital_expression(
        expr, {}, to_time(0), to_time(1), to_time(1e-6)
    )
    assert result == (Pattern([True]) * 500 + Pattern([False]) * 500) * 1000


def test_square_wave_time_offset():
    expr = Expression("square_wave((t - 0.5 ms) / 1 ms)")

    result = evaluate_time_dependent_digital_expression(
        expr, {}, to_time(0), to_time(1), to_time(1e-6)
    )
    assert result == (Pattern([False]) * 500 + Pattern([True]) * 500) * 1000


def test_square_wave_duty_cycle():
    expr = Expression("square_wave(t / 1 ms, 0.1)")

    result = evaluate_time_dependent_digital_expression(
        expr, {}, to_time(0), to_time(1), to_time(1e-6)
    )
    assert result == (Pattern([True]) * 100 + Pattern([False]) * 900) * 1000
