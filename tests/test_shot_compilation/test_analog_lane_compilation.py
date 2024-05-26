import numpy as np

from caqtus.device.sequencer.compilation.compile_analog_lane import (
    compile_analog_lane,
)
from caqtus.device.sequencer.instructions import Pattern
from caqtus.session.shot import TimeLanes
from caqtus.types.timelane import AnalogTimeLane, Ramp
from caqtus.shot_compilation import ShotContext
from caqtus.types.expression import Expression


def test_0():
    lane = AnalogTimeLane([Expression("0 dB"), Expression("10 dB")])
    shot_context = ShotContext(
        device_configurations={},
        time_lanes=TimeLanes(
            step_names=["step1", "step2"], step_durations=[Expression("10 ns")] * 2
        ),
        variables={},
    )
    result = compile_analog_lane(lane, None, 1, shot_context)
    expected = Pattern([1.0]) * 10 + Pattern([10.0]) * 10
    assert np.allclose(result.to_pattern().array, expected.to_pattern().array), str(
        result
    )


def test_1():
    lane = AnalogTimeLane([Expression("0 dB"), Ramp(), Expression("10 dB")])
    shot_context = ShotContext(
        device_configurations={},
        time_lanes=TimeLanes(
            step_names=["step1", "step2", "step3"],
            step_durations=[Expression("10 ns")] * 3,
        ),
        variables={},
    )
    result = compile_analog_lane(lane, None, 1, shot_context)
    expected = (
        10 * [1.0]
        + [
            1.0,
            1.9000000000000008,
            2.8000000000000016,
            3.700000000000001,
            4.600000000000001,
            5.500000000000002,
            6.400000000000002,
            7.300000000000001,
            8.200000000000003,
            9.100000000000003,
        ]
        + 11 * [10.000000000000002]
    )
    assert np.allclose(result.to_pattern().array, expected), str(result)


def test_2():
    lane = AnalogTimeLane([Expression("0 dB"), Ramp(), Expression("10 dB")])
    shot_context = ShotContext(
        device_configurations={},
        time_lanes=TimeLanes(
            step_names=["step1", "step2", "step3"],
            step_durations=[Expression("10 ns")] * 3,
        ),
        variables={},
    )
    result = compile_analog_lane(lane, "dB", 1, shot_context)
    expected = (
        10 * [0.0]
        + [
            0.0,
            2.7875360095282913,
            4.471580313422194,
            5.682017240669951,
            6.627578316815741,
            7.403626894942439,
            8.061799739838872,
            8.633228601204559,
            9.138138523837167,
            9.590413923210937,
        ]
        + 11 * [10.0]
    )
    assert np.allclose(result.to_pattern().array, expected), str(result)


def test_4():
    lane = AnalogTimeLane([Expression("10 Hz"), Expression("1 kHz")])
    shot_context = ShotContext(
        device_configurations={},
        time_lanes=TimeLanes(
            step_names=["step1", "step2"], step_durations=[Expression("10 ns")] * 2
        ),
        variables={},
    )
    result = compile_analog_lane(lane, "Hz", 1, shot_context)
    expected = Pattern([10.0]) * 10 + Pattern([1000.0]) * 10
    assert result == expected, str(result)


def test_5():
    lane = AnalogTimeLane([Expression("t / (10 ns) * 1 Hz")])
    shot_context = ShotContext(
        device_configurations={},
        time_lanes=TimeLanes(
            step_names=["step1"], step_durations=[Expression("10 ns")]
        ),
        variables={},
    )
    result = compile_analog_lane(lane, "Hz", 1, shot_context)
    expected = Pattern([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
    assert np.allclose(result.to_pattern().array, expected.to_pattern().array), str(
        result
    )
