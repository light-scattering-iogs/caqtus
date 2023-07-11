import numpy as np
from pydantic import validator

from settings_model import SettingsModel
from spectum_awg_m4i66xx_x8.runtime import (
    StepName,
    StepConfiguration,
    SegmentName,
    SegmentData,
    StepChangeCondition,
)
from trap_signal_generator.configuration import StaticTrapConfiguration2D
from trap_signal_generator.runtime import StaticTrapGenerator


class MoveConfiguration(SettingsModel):
    """

    Fields:
        initial_config: The initial configuration of the trap.
        final_config: The final configuration of the trap.
        move_duration: The time to move from the initial to the final configuration, in seconds.
        scale_x: The scale factor for the x-axis, in Volt.
        scale_y: The scale factor for the y-axis, in Volt.
    """

    initial_config: StaticTrapConfiguration2D
    final_config: StaticTrapConfiguration2D
    move_duration: float

    @validator("final_config")
    def validate_final_config(cls, v, values):
        if v.sampling_rate != values["initial_config"].sampling_rate:
            raise ValueError(
                "The sampling rate of the final configuration must match the sampling rate of the initial configuration."
            )
        return v


def generate_move(
    move_config: MoveConfiguration,
) -> tuple[dict[StepName, StepConfiguration], dict[SegmentName, SegmentData]]:
    segments = {
        SegmentName("initial"): generate_static_traps_data(move_config.initial_config),
        SegmentName("move"): generate_move_data(
            move_config.initial_config,
            move_config.final_config,
            move_config.move_duration,
        ),
        SegmentName("final"): generate_static_traps_data(move_config.final_config),
    }
    steps = generate_step_configs()
    return steps, segments


def generate_static_traps_data(trap_config: StaticTrapConfiguration2D) -> SegmentData:
    trap_generator_x = StaticTrapGenerator.from_configuration(trap_config.config_x)
    trap_generator_y = StaticTrapGenerator.from_configuration(trap_config.config_y)
    return np.array(
        (trap_generator_x.compute_signal(), trap_generator_y.compute_signal()),
        dtype=np.int16,
    )


def generate_move_data(
    initial_config: StaticTrapConfiguration2D,
    final_config: StaticTrapConfiguration2D,
    move_duration: float,
) -> SegmentData:
    raise NotImplementedError


def generate_step_configs() -> dict[StepName, StepConfiguration]:
    steps = {
        StepName("initial"): StepConfiguration(
            segment=SegmentName("initial"),
            next_step=StepName("move"),
            repetition=1,
            change_condition=StepChangeCondition.ON_TRIGGER,
        ),
        StepName("move"): StepConfiguration(
            segment=SegmentName("move"),
            next_step=StepName("final"),
            repetition=1,
            change_condition=StepChangeCondition.ON_TRIGGER,
        ),
        StepName("final"): StepConfiguration(
            segment=SegmentName("final"),
            next_step=StepName("initial"),
            repetition=1,
            change_condition=StepChangeCondition.ON_TRIGGER,
        ),
    }

    return steps
