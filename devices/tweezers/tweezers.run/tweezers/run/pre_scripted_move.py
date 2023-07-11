import numpy as np
from pydantic import validator

from settings_model import SettingsModel
from spectum_awg_m4i66xx_x8.runtime import (
    StepName,
    StepConfiguration,
    SegmentName,
    SegmentData,
    StepChangeCondition,
    NumberSamples,
)
from trap_signal_generator.configuration import (
    StaticTrapConfiguration2D,
    StaticTrapConfiguration,
)
from trap_signal_generator.runtime import StaticTrapGenerator, MovingTrapGenerator


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
    move_number_samples: int

    @validator("final_config")
    def validate_final_config(cls, v, values):
        initial_config: StaticTrapConfiguration2D = values["initial_config"]
        if v.sampling_rate != initial_config.sampling_rate:
            raise ValueError(
                "The sampling rate of the final configuration must match the sampling rate of the initial configuration."
            )
        if v.number_tones_x != initial_config.number_tones_x:
            raise ValueError(
                "The number of tones in the final configuration must match the number of tones in the initial configuration."
            )
        if v.number_tones_y != initial_config.number_tones_y:
            raise ValueError(
                "The number of tones in the final configuration must match the number of tones in the initial configuration."
            )
        return v

    @property
    def number_tone_x(self) -> int:
        return self.initial_config.number_tones_x

    @property
    def number_tone_y(self) -> int:
        return self.initial_config.number_tones_y

    @property
    def sampling_rate(self) -> float:
        return self.initial_config.sampling_rate


def generate_move(
    move_config: MoveConfiguration,
) -> tuple[dict[StepName, StepConfiguration], dict[SegmentName, SegmentData]]:
    segments = {
        SegmentName("initial"): generate_static_traps_data(move_config.initial_config),
        SegmentName("move"): generate_move_data(
            move_config.initial_config,
            move_config.final_config,
            move_config.move_number_samples,
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
    number_samples: int,
) -> SegmentData:
    move_x = generate_1d_move_data(
        initial_config.config_x,
        final_config.config_x,
        NumberSamples(number_samples),
        initial_config.sampling_rate,
    )
    move_y = generate_1d_move_data(
        initial_config.config_y,
        final_config.config_y,
        NumberSamples(number_samples),
        initial_config.sampling_rate,
    )
    return np.array((move_x, move_y), dtype=np.int16)


def generate_1d_move_data(
    initial_config: StaticTrapConfiguration,
    final_config: StaticTrapConfiguration,
    number_samples: NumberSamples,
    sampling_rate: float,
) -> np.ndarray[NumberSamples, np.int16]:
    moving_generator = MovingTrapGenerator(
        starting_frequencies=initial_config.frequencies,
        target_frequencies=final_config.frequencies,
        starting_phases=2
        * np.pi
        * np.array(initial_config.frequencies)
        * initial_config.number_samples
        / initial_config.sampling_rate
        + np.array(initial_config.phases),
        target_phases=final_config.phases,
        amplitudes=initial_config.amplitudes,
        sampling_rate=sampling_rate,
        number_samples=number_samples,
        trajectory_function="sin",
    )
    return moving_generator.compute_signal().astype(np.int16)


def generate_step_configs() -> dict[StepName, StepConfiguration]:
    steps = {
        StepName("initial"): StepConfiguration(
            segment=SegmentName("initial"),
            next_step=StepName("move"),
            repetition=1,
            change_condition=StepChangeCondition.ON_TRIGGER
        ),
        StepName("move"): StepConfiguration(
            segment=SegmentName("move"),
            next_step=StepName("final"),
            repetition=1,
            change_condition=StepChangeCondition.ALWAYS,
        ),
        StepName("final"): StepConfiguration(
            segment=SegmentName("final"),
            next_step=StepName("initial"),
            repetition=1,
            change_condition=StepChangeCondition.ON_TRIGGER,
        ),
    }

    return steps
