from caqtus.shot_compilation import VariableNamespace
from caqtus.shot_compilation.lane_compilers import DigitalLaneCompiler
from caqtus.device.sequencer.instructions import Pattern
from caqtus.session.shot import DigitalTimeLane
from caqtus.types.expression import Expression
from caqtus.types.units import Quantity


def test_0():
    lane = DigitalTimeLane([True, False])
    lane_compiler = DigitalLaneCompiler(
        lane, ["a", "b"], [Expression("1 s"), Expression("1 s")]
    )
    result = lane_compiler.compile(VariableNamespace(), 1)
    assert result == Pattern([True]) * 1_000_000_000 + Pattern([False]) * 1_000_000_000


def test_1():
    lane = DigitalTimeLane([Expression("a"), Expression("b")])
    lane_compiler = DigitalLaneCompiler(
        lane, ["a", "b"], [Expression("1 s"), Expression("1 s")]
    )
    result = lane_compiler.compile(VariableNamespace({"a": True, "b": False}), 1)

    assert result == Pattern([True]) * 1_000_000_000 + Pattern([False]) * 1_000_000_000


def test_2():
    lane = DigitalTimeLane([True] * 2 + [False])
    lane_compiler = DigitalLaneCompiler(lane, ["a", "b", "c"], [Expression("1 s")] * 3)
    result = lane_compiler.compile(VariableNamespace(), 1)
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
    lane_compiler = DigitalLaneCompiler(lane, lane_names, lane_durations)
    result = lane_compiler.compile(variables, 1)
    assert len(result) == 310_000_001
