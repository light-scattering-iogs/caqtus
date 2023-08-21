import logging

from experiment_control.compute_device_parameters import (
    compile_step_durations,
    compile_digital_lane,
)
from experiment_control.compute_device_parameters.compile_lane import (
    number_ticks,
    get_step_bounds,
)
from sequence.configuration import ShotConfiguration
from digital_lane.configuration import DigitalLane
from sequencer.channel import Concatenate, Repeat, ChannelPattern
from variable.namespace import VariableNamespace

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def test_digital_lane_compilation(
    shot_config: ShotConfiguration, variables: VariableNamespace
) -> None:
    durations = compile_step_durations(
        step_durations=shot_config.step_durations,
        step_names=shot_config.step_names,
        variables=variables,
    )
    logger.debug(f"{get_step_bounds(durations)=}")

    time_step = 50

    lane = shot_config.find_lane("421 cell (AOM)")
    assert isinstance(lane, DigitalLane)
    instruction = compile_digital_lane(durations, lane, variables, time_step)
    assert len(instruction) == number_ticks(0.0, sum(durations), time_step)
    result = Concatenate(
        (
            Repeat(ChannelPattern((True,)), 200000),
            Repeat(ChannelPattern((False,)), 1600000),
            Repeat(ChannelPattern((True,)), 4620001),
            Repeat(ChannelPattern((True,)), 160000),
            Repeat(ChannelPattern((True,)), 2),
            Repeat(ChannelPattern((True,)), 20),
            Repeat(ChannelPattern((True,)), 10),
            Repeat(ChannelPattern((True,)), 3),
            Repeat(ChannelPattern((True,)), 100000),
            Repeat(ChannelPattern((True,)), 600000),
            Repeat(ChannelPattern((False,)), 20000),
            Repeat(ChannelPattern((True,)), 200000),
        )
    )
    logger.debug(f"{instruction=}")
    assert instruction == result
