from collections.abc import Iterable, Sequence

import numpy as np
from pytest import approx, raises

from caqtus.device.sequencer.timing import to_time_step, ns
from caqtus.shot_compilation.lane_compilation._compile_analog_lane import (
    compile_analog_lane,
    evaluate_constant_expression,
    evaluate_time_dependent_expression,
    ConstantBlockResult,
    TimeDependentBlockResult,
)
from caqtus.shot_compilation.timed_instructions import Pattern, create_ramp
from caqtus.shot_compilation.timing import to_time, get_step_bounds, Time
from caqtus.types.expression import Expression
from caqtus.types.recoverable_exceptions import InvalidValueError
from caqtus.types.recoverable_exceptions import RecoverableException
from caqtus.types.timelane import AnalogTimeLane, Ramp
from caqtus.types.units import Unit, InvalidDimensionalityError


def into_time(value) -> Time:
    return Time(to_time_step(value) * ns)


def into_bounds(durations: Iterable[float]) -> Sequence[Time]:
    return get_step_bounds(to_time(duration) for duration in durations)


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
    with raises(InvalidValueError):
        evaluate_constant_expression(expression, variables, length)


def test_evaluate_time_dependent_expression_0():
    expression = Expression("t.magnitude * 1e9")

    variables = {}
    result = evaluate_time_dependent_expression(
        expression, variables, to_time(0), to_time(10e-9), into_time(1)
    )
    assert result == TimeDependentBlockResult(
        values=np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
        unit=None,
        initial_value=0,
        final_value=10,
    )


def test_evaluate_time_dependent_expression_1():
    expression = Expression("t * 1e9")

    variables = {}

    result = evaluate_time_dependent_expression(
        expression, variables, to_time(0), to_time(10e-9), into_time(1)
    )

    assert result == TimeDependentBlockResult(
        values=np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
        unit=Unit("s"),
        initial_value=0,
        final_value=10,
    )


def test_evaluate_time_dependent_expression_2():
    expression = Expression("(10 dB) * t / (10 ns)")

    variables = {}

    result = evaluate_time_dependent_expression(
        expression, variables, to_time(0), to_time("10e-9"), into_time(1)
    )

    assert result == TimeDependentBlockResult(
        values=np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
        unit=None,
        initial_value=0,
        final_value=10,
    )


def test_logarithmic_expression():
    lane = AnalogTimeLane([Expression("0 dB"), Expression("10 dB")])
    result = compile_analog_lane(lane, {}, into_bounds([10e-9, 10e-9]), into_time(1))
    expected = Pattern([1]) * 10 + Pattern([10]) * 10
    assert result.values == approx(expected)
    assert result.units is None


def test_ramp():
    lane = AnalogTimeLane([Expression("0"), Ramp(), Expression("10")])
    result = compile_analog_lane(lane, {}, into_bounds([0, 4e-9, 0]), into_time(1))
    expected = create_ramp(0, 10, 4)

    assert result.values == expected
    assert result.units is None


def test_ramp_zero_duration():
    lane = AnalogTimeLane([Expression("0"), Ramp(), Expression("10")])
    result = compile_analog_lane(lane, {}, into_bounds([10e-9, 0, 5e-9]), into_time(1))
    expected = Pattern([0]) * 10 + Pattern([10]) * 5

    assert result.values == approx(expected)
    assert result.units is None


def test_ramp_2():
    lane = AnalogTimeLane([Expression("10 V"), Ramp(), Expression("100 mV")])
    result = compile_analog_lane(
        lane,
        {},
        into_bounds([1e-8, 2e-8, 3e-8]),
        into_time(10),
    )
    expected = Pattern([10]) * 1 + create_ramp(10, 0.1, 2) + Pattern([0.1]) * 3

    assert result.values == approx(expected)
    assert result.units == Unit("V")


def test_logarithmic_ramp():
    lane = AnalogTimeLane([Expression("0 dB"), Ramp(), Expression("10 dB")])
    result = compile_analog_lane(
        lane, {}, into_bounds([3e-9, 4e-9, 3e-9]), into_time(1)
    )
    expected = Pattern([1.0]) * 3 + create_ramp(1, 10, 4) + 3 * Pattern([10.0])

    assert result.values == approx(expected)
    assert result.units is None


def test_ramp_time_dependent():
    lane = AnalogTimeLane([Expression("2 * t"), Ramp(), Expression("t")])
    result = compile_analog_lane(
        lane, {}, into_bounds([10e-9, 10e-9, 10e-9]), into_time(1)
    )
    expected = (
        Pattern(np.linspace(0, 20, 10, endpoint=False) * 1e-9)
        + create_ramp(20e-9, 0, 10)
        + Pattern(np.linspace(0, 10, 10, endpoint=False) * 1e-9)
    )

    assert result.values == approx(expected)
    assert result.units == Unit("s")


def test_non_integer_ramp():
    lane = AnalogTimeLane([Expression("0"), Ramp(), Expression("1")])
    result = compile_analog_lane(
        lane, {}, into_bounds([0.5e-9, 2e-9, 1.5e-9]), into_time(1)
    )
    expected = Pattern([0, 1 / 4, 3 / 4, 1])
    assert result.values == approx(expected)
    assert result.units is None


def test_expression_with_unit():
    lane = AnalogTimeLane([Expression("10 Hz"), Expression("1 kHz")])
    result = compile_analog_lane(lane, {}, into_bounds([10e-9, 10e-9]), into_time(1))
    expected = Pattern([10.0]) * 10 + Pattern([1000.0]) * 10
    assert result.values == approx(expected)
    assert result.units == Unit("1/s")


def test_time_dependent_expression():
    lane = AnalogTimeLane([Expression("t / (10 ns) * 1 Hz")])
    result = compile_analog_lane(lane, {}, into_bounds([10e-9]), into_time(1))
    expected = Pattern([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])

    assert result.values == approx(expected)
    assert result.units == Unit("1/s")


def test_invalid_expression_cell():
    lane = AnalogTimeLane([Expression("...")])
    with raises(RecoverableException):
        compile_analog_lane(lane, {}, into_bounds([10e-9]), into_time(1))


def test_invalid_dimensions():
    lane = AnalogTimeLane([Expression("1"), Expression("1 Hz")])

    with raises(InvalidDimensionalityError):
        compile_analog_lane(lane, {}, into_bounds([10e-9, 10e-9]), into_time(1))


def test_invalid_ramp():
    lane = AnalogTimeLane([Expression("1"), Ramp()])

    with raises(InvalidValueError):
        compile_analog_lane(lane, {}, into_bounds([10e-9, 10e-9]), into_time(1))


def test_invalid_ramp_2():
    lane = AnalogTimeLane([Ramp(), Expression("1")])

    with raises(InvalidValueError):
        compile_analog_lane(lane, {}, into_bounds([10e-9, 10e-9]), into_time(1))


def test_invalid_ramp_3():
    lane = AnalogTimeLane([Expression("1"), Ramp(), Ramp(), Expression("1")])

    with raises(InvalidValueError):
        compile_analog_lane(
            lane, {}, into_bounds([10e-9, 10e-9, 10e-9, 10e-9]), into_time(1)
        )
