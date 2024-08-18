import numpy as np
import pytest
from hypothesis import given, example
from hypothesis.strategies import floats, tuples, lists

# noinspection PyProtectedMember
from caqtus.device.sequencer.channel_commands._calibrated_analog_mapping import (
    DimensionlessCalibration,
)
from caqtus.device.sequencer.instructions import (
    SequencerInstruction,
    Ramp,
    ramp,
    Pattern,
)
from ..test_instructions import analog_instruction, pattern, ramp_strategy

calibration = lists(
    tuples(
        floats(allow_nan=False, allow_infinity=False, min_value=-1e3, max_value=1e3),
        floats(allow_nan=False, allow_infinity=False, min_value=-1e3, max_value=1e3),
    ),
    min_size=2,
    max_size=50,
).map(DimensionlessCalibration)


@given(calibration, pattern(np.float64, min_length=1, max_length=100))
@example(
    cal=DimensionlessCalibration(
        [(0.0, 0.0), (-1.5, 0.0), (-1.1754943508222875e-38, 999.9999999999999)],
    ),
    p=Pattern([-1.17549435e-38, 0.00000000e00]),
)
@example(
    cal=DimensionlessCalibration(
        [(3.063778061920068e-211, -83.0), (-1.0, 941.9999999999999)],
    ),
    p=Pattern([-1.0, 0.0]),
)
@example(
    cal=DimensionlessCalibration(
        [(1.581407700243433e-47, 0.01562500000000022), (-1.0, -1.0)],
    ),
    p=Pattern([0.0]),
)
@example(
    cal=DimensionlessCalibration(
        [(2.225073858507e-311, 1.0), (-2.2250738585e-313, 0.0)],
    ),
    p=Pattern([0.0]),
)
def test_calibration_pattern(
    cal: DimensionlessCalibration, p: SequencerInstruction[np.floating]
):
    try:
        computed = cal.apply(p).to_pattern().array
    except FloatingPointError:
        pass
    else:
        assert np.all(np.isfinite(computed))
        assert np.all(computed >= min(cal.output_points)) or np.allclose(
            np.min(computed), min(cal.output_points)
        ), f"Computed: {computed}\nMin: {min(cal.output_points)}"
        assert np.all(computed <= max(cal.output_points)) or np.allclose(
            np.max(computed), max(cal.output_points)
        )


@given(calibration, ramp_strategy())
@example(
    cal=DimensionlessCalibration([(0.0, 0.0), (0.0, 1.0)]),
    instr=ramp(start=0.0, stop=-1.0, length=3),
)
@example(
    cal=DimensionlessCalibration([(0.0, 0.0), (-2.220446049250313e-16, 1.0)]),
    instr=ramp(start=np.float64(-0.5), stop=np.float64(0.5), length=98),
)
def test_calibration_ramp(cal, instr: Ramp):
    validate_calibration(cal, instr)


def validate_calibration(
    cal: DimensionlessCalibration, instr: SequencerInstruction[np.floating]
):
    try:
        computed = cal.apply(instr).to_pattern().array
        expected = cal.apply(instr.to_pattern()).to_pattern().array
    except FloatingPointError:
        pass
    else:
        assert np.allclose(computed, expected)


@pytest.mark.parametrize(
    "cal, instr",
    [
        (DimensionlessCalibration([(0, 0), (1, 2)]), ramp(0, 1, 10)),
        (DimensionlessCalibration([(0, 0), (1, 2)]), ramp(0.5, 0.5, 10)),
        (DimensionlessCalibration([(0.0, 0.0), (2.0, 0.0)]), ramp(1.0, 2.0, 1)),
        (DimensionlessCalibration([(0.0, 0.0), (1.0, 0.0)]), ramp(1.0, -1.0, 1)),
        (DimensionlessCalibration([(0.0, 0.0), (1.0, 0.0)]), ramp(-1.0, +1.0, 1)),
        (DimensionlessCalibration([(0.0, 1.0), (1.0, 0.0)]), ramp(4.0, 0.0, 2)),
        (DimensionlessCalibration([(-1.0, 0.0), (0.0, 1.0)]), ramp(0.0, -4.0, 2)),
        (DimensionlessCalibration([(-1.0, 0.0), (0.0, 1.0)]), ramp(0.5, -1.0, 3)),
    ],
)
def test_calibration_on_ramp(cal: DimensionlessCalibration, instr: Ramp):
    validate_calibration(cal, instr)


@given(calibration, analog_instruction(max_length=1000))
def test_calibration_apply(
    cal: DimensionlessCalibration, instr: SequencerInstruction[np.floating]
):
    validate_calibration(cal, instr)
