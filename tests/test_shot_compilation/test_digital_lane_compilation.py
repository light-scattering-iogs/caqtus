from caqtus.device.sequencer.compilation._compile_digital_lane import (
    compile_digital_lane,
)
from caqtus.device.sequencer.instructions import Pattern
from caqtus.session.shot import DigitalTimeLane, TimeLanes
from caqtus.shot_compilation import VariableNamespace, ShotContext
from caqtus.types.expression import Expression
from caqtus.types.units import Quantity
from caqtus.types.variable_name import DottedVariableName


def test_0():
    shot_context = ShotContext(
        device_configurations={},
        time_lanes=TimeLanes(
            step_names=["a", "b"], step_durations=[Expression("1 s"), Expression("1 s")]
        ),
        variables={},
    )
    lane = DigitalTimeLane([True, False])
    result = compile_digital_lane(lane, 1, shot_context)
    assert result == Pattern([True]) * 1_000_000_000 + Pattern([False]) * 1_000_000_000


def test_1():
    shot_context = ShotContext(
        device_configurations={},
        time_lanes=TimeLanes(
            step_names=["a", "b"], step_durations=[Expression("1 s"), Expression("1 s")]
        ),
        variables={DottedVariableName("a"): True, DottedVariableName("b"): False},
    )
    lane = DigitalTimeLane([Expression("a"), Expression("b")])
    result = compile_digital_lane(lane, 1, shot_context)

    assert result == Pattern([True]) * 1_000_000_000 + Pattern([False]) * 1_000_000_000


def test_2():
    shot_context = ShotContext(
        device_configurations={},
        time_lanes=TimeLanes(
            step_names=["a", "b", "c"],
            step_durations=[Expression("1 s")] * 3,
        ),
        variables={},
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
        device_configurations={},
        time_lanes=TimeLanes(
            step_names=lane_names,
            step_durations=lane_durations,
        ),
        variables=variables.dict(),
    )
    result = compile_digital_lane(lane, 1, shot_context)
    assert len(result) == 310_000_001
