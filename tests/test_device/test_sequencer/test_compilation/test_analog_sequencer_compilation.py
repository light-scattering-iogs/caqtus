from typing import Type

import pytest

from caqtus.device import DeviceName
from caqtus.device.sequencer import (
    SequencerConfiguration,
    SequencerCompiler,
    ChannelConfiguration,
    AnalogChannelConfiguration,
)
from caqtus.device.sequencer.channel_commands import LaneValues, CalibratedAnalogMapping
from caqtus.device.sequencer.timing import to_time_step
from caqtus.device.sequencer.trigger import SoftwareTrigger
from caqtus.shot_compilation.compilation_contexts import SequenceContext, ShotContext
from caqtus.shot_compilation.timed_instructions import Pattern, create_ramp
from caqtus.types.expression import Expression
from caqtus.types.timelane import TimeLanes, AnalogTimeLane, Ramp


class MockSequencerConfiguration(SequencerConfiguration):
    def channel_types(self) -> tuple[Type[ChannelConfiguration], ...]:
        return AnalogChannelConfiguration, AnalogChannelConfiguration


@pytest.fixture
def sequencer_config() -> SequencerConfiguration:
    return MockSequencerConfiguration(
        remote_server=None,
        time_step=to_time_step(10),
        trigger=SoftwareTrigger(),
        channels=(
            AnalogChannelConfiguration(
                description="Channel 0", output=LaneValues("test"), output_unit="V"
            ),
            AnalogChannelConfiguration(
                description="Channel 1",
                output=CalibratedAnalogMapping(
                    input_=LaneValues("test 1"),
                    input_units="dB",
                    output_units="V",
                    measured_data_points=((0, 1), (10, 10)),
                ),
                output_unit="V",
            ),
        ),
    )


def test_multiple_analog_lane(sequencer_config):
    time_lanes = TimeLanes(
        step_names=["step 0", "step 1", "step 2"],
        step_durations=[Expression("10 ns"), Expression("20 ns"), Expression("30 ns")],
        lanes={
            "test": AnalogTimeLane([Expression("10 V"), Ramp(), Expression("100 mV")]),
            "test 1": AnalogTimeLane([Expression("0 dB"), Ramp(), Expression("10 dB")]),
        },
    )
    sequence_context = SequenceContext(
        {DeviceName("sequencer"): sequencer_config}, time_lanes
    )

    shot_context = ShotContext(sequence_context, {}, {})
    compiler = SequencerCompiler(
        DeviceName("sequencer"), shot_context._sequence_context
    )
    result = compiler.compile_shot_parameters(shot_context)
    sequence = result["sequence"]
    assert sequence["ch 0"] == pytest.approx(
        Pattern([10]) * 1 + create_ramp(10, 0.1, 2) + Pattern([0.1]) * 3
    )
    assert sequence["ch 1"] == pytest.approx(
        Pattern([1]) * 1 + create_ramp(1, 10, 2) + Pattern([10]) * 3
    )
