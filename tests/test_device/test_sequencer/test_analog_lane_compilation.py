import numpy as np
import pytest

from caqtus.device.sequencer.channel_commands._channel_sources.compile_analog_lane import (
    evaluate_constant_expression,
    evaluate_time_dependent_expression,
    ConstantBlockResult,
    TimeDependentBlockResult,
)
from caqtus.types.expression import Expression
from caqtus.types.recoverable_exceptions import InvalidValueError
from caqtus.types.units import Unit


def test_evaluate_constant_expression_0():
    expression = Expression("1 MHz")
    variables = {}
    length = 1
    result = evaluate_constant_expression(expression, variables, length)
    assert result == ConstantBlockResult(1e6, 1, Unit("Hz"))


def test_evaluate_constant_expression_1():
    expression = Expression("0 dB")
    variables = {}
    length = 1
    result = evaluate_constant_expression(expression, variables, length)
    assert result == ConstantBlockResult(1, 1, None)


def test_evaluate_constant_expression_2():
    expression = Expression("0")
    variables = {}
    length = 1
    result = evaluate_constant_expression(expression, variables, length)
    assert result == ConstantBlockResult(0, 1, None)


def test_evaluate_constant_expression_3():
    expression = Expression("...")
    variables = {}
    length = 1
    with pytest.raises(InvalidValueError):
        evaluate_constant_expression(expression, variables, length)


def test_evaluate_time_dependent_expression_0():
    expression = Expression("t.magnitude * 1e9")

    variables = {}

    result = evaluate_time_dependent_expression(expression, variables, 0, 10e-9, 1)

    assert result == TimeDependentBlockResult(
        values=np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
        unit=None,
        initial_value=0,
        final_value=10,
    )


def test_evaluate_time_dependent_expression_1():
    expression = Expression("t * 1e9")

    variables = {}

    result = evaluate_time_dependent_expression(expression, variables, 0, 10e-9, 1)

    assert result == TimeDependentBlockResult(
        values=np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
        unit=Unit("s"),
        initial_value=0,
        final_value=10,
    )


def test_evaluate_time_dependent_expression_2():
    expression = Expression("(10 dB) * t / (10 ns)")

    variables = {}

    result = evaluate_time_dependent_expression(expression, variables, 0, 10e-9, 1)

    assert result == TimeDependentBlockResult(
        values=np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
        unit=None,
        initial_value=0,
        final_value=10,
    )
