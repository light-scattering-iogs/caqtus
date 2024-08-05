from typing import Type

import pytest

from caqtus.device import DeviceName
from caqtus.device.sequencer import (
    SequencerConfiguration,
    SoftwareTrigger,
    SequencerCompiler,
    ChannelConfiguration,
    AnalogChannelConfiguration,
)
from caqtus.device.sequencer.channel_commands import LaneValues
from caqtus.device.sequencer.instructions import Pattern, ramp
from caqtus.shot_compilation.compilation_contexts import SequenceContext, ShotContext
from caqtus.types.expression import Expression
from caqtus.types.timelane import TimeLanes, AnalogTimeLane, Ramp


class MockSequencerConfiguration(SequencerConfiguration):
    @classmethod
    def channel_types(cls) -> tuple[Type[ChannelConfiguration], ...]:
        return (AnalogChannelConfiguration,)


@pytest.fixture
def sequencer_config() -> SequencerConfiguration:
    return MockSequencerConfiguration(
        remote_server=None,
        time_step=10,
        trigger=SoftwareTrigger(),
        channels=(
            AnalogChannelConfiguration(
                description="Channel 0", output=LaneValues("test"), output_unit="V"
            ),
        ),
    )


def test_single_analog_lane(sequencer_config):
    time_lanes = TimeLanes(
        step_names=["step 0", "step 1", "step 2"],
        step_durations=[Expression("10 ns"), Expression("20 ns"), Expression("30 ns")],
        lanes={
            "test": AnalogTimeLane([Expression("10 V"), Ramp(), Expression("100 mV")])
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
    assert sequence["ch 0"][:-1] == pytest.approx(
        Pattern([10]) * 1 + ramp(10, 0.1, 2) + Pattern([0.1]) * 3
    )
