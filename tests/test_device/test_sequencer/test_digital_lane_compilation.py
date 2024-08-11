import decimal

import pytest

from caqtus.device.sequencer.channel_commands._channel_sources._compile_digital_lane import (
    compile_digital_lane,
)
from caqtus.device.sequencer.instructions import Pattern
from caqtus.session.shot import DigitalTimeLane, TimeLanes
from caqtus.shot_compilation import VariableNamespace, ShotContext, SequenceContext
from caqtus.types.expression import Expression
from caqtus.types.recoverable_exceptions import RecoverableException
from caqtus.types.units import Quantity
from caqtus.types.variable_name import DottedVariableName


def test_0():
    shot_context = ShotContext(
        SequenceContext(
            device_configurations={},
            time_lanes=TimeLanes(
                step_names=["a", "b"],
                step_durations=[Expression("1 s"), Expression("1 s")],
            ),
        ),
        variables={},
        device_compilers={},
    )
    lane = DigitalTimeLane([True, False])
    result = compile_digital_lane(lane, 1, shot_context)
    assert result == Pattern([True]) * 1_000_000_000 + Pattern([False]) * 1_000_000_000


def test_1():
    shot_context = ShotContext(
        SequenceContext(
            device_configurations={},
            time_lanes=TimeLanes(
                step_names=["a", "b"],
                step_durations=[Expression("1 s"), Expression("1 s")],
            ),
        ),
        variables={DottedVariableName("a"): True, DottedVariableName("b"): False},
        device_compilers={},
    )
    lane = DigitalTimeLane([Expression("a"), Expression("b")])
    result = compile_digital_lane(lane, 1, shot_context)

    assert result == Pattern([True]) * 1_000_000_000 + Pattern([False]) * 1_000_000_000


def test_2():
    shot_context = ShotContext(
        SequenceContext(
            device_configurations={},
            time_lanes=TimeLanes(
                step_names=["a", "b", "c"],
                step_durations=[Expression("1 s")] * 3,
            ),
        ),
        variables={},
        device_compilers={},
    )
    lane = DigitalTimeLane([True] * 2 + [False])
    result = compile_digital_lane(lane, 1, shot_context)
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
            device_configurations={},
            time_lanes=TimeLanes(
                step_names=lane_names,
                step_durations=lane_durations,
            ),
        ),
        variables=variables.dict(),
        device_compilers={},
    )
    result = compile_digital_lane(lane, 1, shot_context)
    assert len(result) == 310_000_001


# test for issue #23
def test_invalid_expression_cell():
    shot_context = ShotContext(
        SequenceContext(
            device_configurations={},
            time_lanes=TimeLanes(
                step_names=["a"],
                step_durations=[Expression("1 s")],
            ),
        ),
        variables={},
        device_compilers={},
    )
    lane = DigitalTimeLane([Expression("...")])
    with pytest.raises(RecoverableException):
        compile_digital_lane(lane, 1, shot_context)


def test_non_integer_time_step():
    shot_context = ShotContext(
        SequenceContext(
            device_configurations={},
            time_lanes=TimeLanes(
                step_names=["a", "b"],
                step_durations=[Expression("1 s"), Expression("1 s")],
            ),
        ),
        variables={},
        device_compilers={},
    )
    lane = DigitalTimeLane([True, False])
    result = compile_digital_lane(lane, decimal.Decimal(0.5), shot_context)
    assert result == Pattern([True]) * 2_000_000_000 + Pattern([False]) * 2_000_000_000
