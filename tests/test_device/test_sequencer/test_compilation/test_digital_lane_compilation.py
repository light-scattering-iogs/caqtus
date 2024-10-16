import decimal

import pytest

from caqtus.device.sequencer.timing import to_time_step, ns
from caqtus.shot_compilation import ShotContext, SequenceContext
from caqtus.shot_compilation.lane_compilation import compile_digital_lane
from caqtus.shot_compilation.timed_instructions import Pattern
from caqtus.shot_compilation.timing import Time, number_ticks
from caqtus.types._parameter_namespace import VariableNamespace
from caqtus.types.expression import Expression
from caqtus.types.recoverable_exceptions import RecoverableException
from caqtus.types.timelane import DigitalTimeLane, TimeLanes
from caqtus.types.units import Quantity
from caqtus.types.variable_name import DottedVariableName


def into_time(value) -> Time:
    return Time(to_time_step(value) * ns)


def test_0():
    shot_context = ShotContext(
        SequenceContext(
            device_configurations={},  # type: ignore[reportCallIssue]
            time_lanes=TimeLanes(  # type: ignore[reportCallIssue]
                step_names=["a", "b"],
                step_durations=[Expression("1 s"), Expression("1 s")],
            ),
        ),
        variables={},  # type: ignore[reportCallIssue]
        device_compilers={},  # type: ignore[reportCallIssue]
    )
    lane = DigitalTimeLane([True, False])
    result = compile_digital_lane(
        lane,
        shot_context.get_step_start_times(),
        into_time(1),
        shot_context.get_parameters(),
    )
    assert result == Pattern([True]) * 1_000_000_000 + Pattern([False]) * 1_000_000_000


def test_1():
    shot_context = ShotContext(
        SequenceContext(
            device_configurations={},  # type: ignore[reportCallIssue]
            time_lanes=TimeLanes(  # type: ignore[reportCallIssue]
                step_names=["a", "b"],
                step_durations=[Expression("1 s"), Expression("1 s")],
            ),
        ),
        variables={DottedVariableName("a"): True, DottedVariableName("b"): False},  # type: ignore[reportCallIssue]
        device_compilers={},  # type: ignore[reportCallIssue]
    )
    lane = DigitalTimeLane([Expression("a"), Expression("b")])
    result = compile_digital_lane(
        lane,
        shot_context.get_step_start_times(),
        into_time(1),
        shot_context.get_parameters(),
    )

    assert result == Pattern([True]) * 1_000_000_000 + Pattern([False]) * 1_000_000_000


def test_2():
    shot_context = ShotContext(
        SequenceContext(
            device_configurations={},  # type: ignore[reportCallIssue]
            time_lanes=TimeLanes(  # type: ignore[reportCallIssue]
                step_names=["a", "b", "c"],
                step_durations=[Expression("1 s")] * 3,
            ),
        ),
        variables={},  # type: ignore[reportCallIssue]
        device_compilers={},  # type: ignore[reportCallIssue]
    )
    lane = DigitalTimeLane([True] * 2 + [False])
    result = compile_digital_lane(
        lane,
        shot_context.get_step_start_times(),
        into_time(1),
        shot_context.get_parameters(),
    )
    assert (
        result == Pattern([True]) * 2_000_000_000 + Pattern([False]) * 1_000_000_000
    ), str(result)


def test_3():
    lane_names = [
        "load MOT",
        "ramp MOT",
        "red MOT",
        "picture",
        "remove atoms",
        "light on",
        "background",
        "nothing",
        "stop",
    ]
    lane_durations = [
        Expression("mot_loading.duration"),
        Expression("red_mot.ramp_duration"),
        Expression("30 ms"),
        Expression("exposure"),
        Expression("20 ms"),
        Expression("5 ms"),
        Expression("exposure"),
        Expression("5 ms"),
        Expression("10 ms"),
    ]
    lane = DigitalTimeLane(
        [
            True,
            False,
            True,
            True,
            True,
            True,
            True,
            True,
            True,
        ]
    )
    variables = VariableNamespace(
        {
            "mot_loading": {
                "duration": Quantity(100, "millisecond"),
            },
            "red_mot": {
                "ramp_duration": Quantity(80, "millisecond"),
            },
            "exposure": Quantity(30, "millisecond"),
        }
    )
    shot_context = ShotContext(
        SequenceContext(
            device_configurations={},  # type: ignore[reportCallIssue]
            time_lanes=TimeLanes(  # type: ignore[reportCallIssue]
                step_names=lane_names,
                step_durations=lane_durations,
            ),
        ),
        variables=variables.dict(),  # type: ignore[reportCallIssue]
        device_compilers={},  # type: ignore[reportCallIssue]
    )
    time_step = into_time(1)
    result = compile_digital_lane(
        lane,
        shot_context.get_step_start_times(),
        time_step,
        shot_context.get_parameters(),
    )
    assert len(result) == number_ticks(
        Time(decimal.Decimal(0)), shot_context.get_shot_duration(), time_step
    )


# test for issue #23
def test_invalid_expression_cell():
    shot_context = ShotContext(
        SequenceContext(
            device_configurations={},  # type: ignore[reportCallIssue]
            time_lanes=TimeLanes(  # type: ignore[reportCallIssue]
                step_names=["a"],
                step_durations=[Expression("1 s")],
            ),
        ),
        variables={},  # type: ignore[reportCallIssue]
        device_compilers={},  # type: ignore[reportCallIssue]
    )
    lane = DigitalTimeLane([Expression("...")])
    with pytest.raises(RecoverableException):
        compile_digital_lane(
            lane,
            shot_context.get_step_start_times(),
            into_time(1),
            shot_context.get_parameters(),
        )


def test_non_integer_time_step():
    shot_context = ShotContext(
        SequenceContext(
            device_configurations={},  # type: ignore[reportCallIssue]
            time_lanes=TimeLanes(  # type: ignore[reportCallIssue]
                step_names=["a", "b"],
                step_durations=[Expression("1 s"), Expression("1 s")],
            ),
        ),
        variables={},  # type: ignore[reportCallIssue]
        device_compilers={},  # type: ignore[reportCallIssue]
    )
    lane = DigitalTimeLane([True, False])
    result = compile_digital_lane(
        lane,
        shot_context.get_step_start_times(),
        into_time(0.5),
        shot_context.get_parameters(),
    )
    assert result == Pattern([True]) * 2_000_000_000 + Pattern([False]) * 2_000_000_000
