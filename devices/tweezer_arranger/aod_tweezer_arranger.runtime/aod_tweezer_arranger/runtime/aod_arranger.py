import logging
import math
from collections.abc import Iterable
from typing import TypeVar, Sequence

import numpy as np
from pydantic import validator

from aod_tweezer_arranger.configuration import AODTweezerConfiguration
from duration_timer import DurationTimerLog
from log_exception import log_exception
from spectum_awg_m4i66xx_x8.configuration import (
    ChannelSettings,
)
from spectum_awg_m4i66xx_x8.runtime import (
    SpectrumAWGM4i66xxX8,
    SegmentName,
    StepName,
    StepConfiguration,
    SegmentData,
)
from tweezer_arranger.configuration import (
    ArrangerInstruction,
    HoldTweezers,
    MoveTweezers,
    RearrangeTweezers,
)
from tweezer_arranger.configuration import (
    TweezerConfigurationName,
)
from tweezer_arranger.runtime import TweezerArranger
from .signal_generator import AWGSignalArray, SignalGenerator, NumberSamples

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class AODTweezerArranger(TweezerArranger[AODTweezerConfiguration]):
    """Device that uses an AWG/AOD to rearrange and move tweezers.

    Fields:
        awg_board_id: The ID of the AWG board to use. Must be a SpectrumAWGM4i66xxX8 board.
        awg_max_power_x: The maximum power that can be output by the AWG on the X axis, in dBm.
        awg_max_power_y: The maximum power that can be output by the AWG on the Y axis, in dBm.
    """

    awg_board_id: str
    awg_max_power_x: float
    awg_max_power_y: float

    _awg: SpectrumAWGM4i66xxX8
    _static_signals: dict[TweezerConfigurationName, SegmentData] = {}
    _signal_generator: SignalGenerator

    @validator("tweezer_configurations")
    def validate_tweezer_configurations(
        cls, configurations: dict[TweezerConfigurationName, AODTweezerConfiguration]
    ) -> dict[TweezerConfigurationName, AODTweezerConfiguration]:
        first_config = first(configurations.values())
        for config in configurations.values():
            if config.scale_x != first_config.scale_x:
                raise ValueError(
                    "All AODTweezerConfigurations must have the same scale_x"
                )
            if config.scale_y != first_config.scale_y:
                raise ValueError(
                    "All AODTweezerConfigurations must have the same scale_y"
                )
            if config.sampling_rate != first_config.sampling_rate:
                raise ValueError(
                    "All AODTweezerConfigurations must have the same sampling_rate"
                )
        return configurations

    @log_exception(logger)
    def initialize(self) -> None:
        super().initialize()
        self._signal_generator = self._enter_context(
            SignalGenerator(self.sampling_rate)
        )
        self._awg = self._prepare_awg()
        self._enter_context(self._awg)
        self._compute_static_signals()
        self._write_static_segments()

    def _prepare_awg(self) -> SpectrumAWGM4i66xxX8:
        return SpectrumAWGM4i66xxX8(
            name=f"{self.name}_awg",
            board_id=self.awg_board_id,
            channel_settings=(
                ChannelSettings(
                    name="X",
                    enabled=True,
                    amplitude=self.scale_x,
                    maximum_power=self.awg_max_power_x,
                ),
                ChannelSettings(
                    name="Y",
                    enabled=True,
                    amplitude=self.scale_y,
                    maximum_power=self.awg_max_power_y,
                ),
            ),
            segment_names=_get_segment_names(self.tweezer_sequence),
            steps=_get_steps(self.tweezer_sequence),
            first_step=static_step_names(0)[0],
            sampling_rate=self.sampling_rate,
        )

    def _compute_static_signals(self):
        for (
            tweezer_configuration_name,
            tweezer_configuration,
        ) in self.tweezer_configurations.items():
            with DurationTimerLog(
                logger, f"Computing static signal for {tweezer_configuration_name}"
            ):
                signals = _compute_static_signal(
                    self._signal_generator, tweezer_configuration
                )
                self._static_signals[tweezer_configuration_name] = np.array(
                    signals, dtype=np.int16
                )

    def _write_static_segments(self) -> None:
        segment_data: dict[SegmentName, SegmentData] = {}
        for step, instruction in enumerate(self.tweezer_sequence):
            if isinstance(instruction, HoldTweezers):
                static_segment = static_segment_names(step)[0]
                segment_data[static_segment] = self._static_signals[
                    instruction.tweezer_configuration
                ]
        last_segment = static_segment_names(len(self.tweezer_sequence))[0]
        last_tweezer_config = self.tweezer_sequence[-1]
        if not isinstance(last_tweezer_config, HoldTweezers):
            raise ValueError(
                "Last instruction in tweezer_sequence must be HoldTweezers"
            )
        segment_data[last_segment] = self._static_signals[
            last_tweezer_config.tweezer_configuration
        ]

        with DurationTimerLog(logger, "Writing static segments"):
            self._awg.update_parameters(segment_data=segment_data)

    @property
    def sampling_rate(self) -> int:
        first_config = first(self.tweezer_configurations.values())
        return round(first_config.sampling_rate)

    @property
    def scale_x(self) -> float:
        first_config = first(self.tweezer_configurations.values())
        return first_config.scale_x

    @property
    def scale_y(self) -> float:
        first_config = first(self.tweezer_configurations.values())
        return first_config.scale_y

    @log_exception(logger)
    def update_parameters(self, *, tweezer_sequence_durations: Sequence[float]) -> None:
        if not len(tweezer_sequence_durations) == len(self.tweezer_sequence):
            raise ValueError(
                "tweezer_sequence_durations must be the same length as tweezer_sequence"
            )
        # this is a limitation of the AWG that each segment must have a length
        # that is a multiple of 32.
        time_step = 32 / self.sampling_rate
        step_repetitions = dict[StepName, int]()
        segment_data: dict[SegmentName, SegmentData] = {}
        for step, (instruction, (start, stop)) in enumerate(
            zip(self.tweezer_sequence, get_step_bounds(tweezer_sequence_durations))
        ):
            ticks = number_ticks(start, stop, time_step)
            if isinstance(instruction, HoldTweezers):
                segment_tick_duration = (
                    self.tweezer_configurations[
                        instruction.tweezer_configuration
                    ].number_samples
                    // 32
                )
                repetitions, remainder = divmod(ticks, segment_tick_duration)

                step_repetitions[static_step_names(step)[0]] = repetitions
                segment_data[static_segment_names(step)[1]] = self._static_signals[
                    instruction.tweezer_configuration
                ][:, : remainder * 32]
            elif isinstance(instruction, MoveTweezers):
                number_samples = NumberSamples(ticks * 32)
                initial_config = self.tweezer_configurations[instruction.initial_tweezer_configuration]
                final_config = self.tweezer_configurations[instruction.final_tweezer_configuration]
                move_signal_x = self._signal_generator.generate_signal_moving_traps(
                    initial_config.amplitudes_x,
                    final_config.amplitudes_x,
                    initial_config.frequencies_x,
                    final_config.frequencies_x,
                    initial_config.phases_x,
                    final_config.phases_x,
                    number_samples,
                )
                move_signal_y = self._signal_generator.generate_signal_moving_traps(
                    initial_config.amplitudes_y,
                    final_config.amplitudes_y,
                    initial_config.frequencies_y,
                    final_config.frequencies_y,
                    initial_config.phases_y,
                    final_config.phases_y,
                    number_samples,
                )
                segment_data[move_segment_name(step)] = np.array(move_signal_x, move_signal_y, dtype=np.int16)
            else:
                raise NotImplementedError
        with DurationTimerLog(logger, "Updating awg parameters"):
            self._awg.update_parameters(
                segment_data=segment_data, step_repetitions=step_repetitions
            )

    def start_sequence(self) -> None:
        self._awg.stop_sequence()
        self._awg.start_sequence(external_trigger=True)

    def has_sequence_finished(self) -> bool:
        current_step = self._awg.get_current_step()
        logger.debug(f"Current step: {current_step}")
        return current_step == static_step_names(len(self.tweezer_sequence))[0]

    @classmethod
    def exposed_remote_methods(cls) -> tuple[str, ...]:
        return super().exposed_remote_methods() + (
            "start_sequence",
            "has_sequence_finished",
        )


def _compute_static_signal(
    signal_generator: SignalGenerator, tweezer_configuration: AODTweezerConfiguration
) -> tuple[AWGSignalArray, AWGSignalArray]:
    static_signal_x = signal_generator.generate_signal_static_traps(
        np.array(tweezer_configuration.amplitudes_x),
        np.array(tweezer_configuration.frequencies_x),
        np.array(tweezer_configuration.phases_x),
        NumberSamples(tweezer_configuration.number_samples),
    )
    static_signal_y = signal_generator.generate_signal_static_traps(
        np.array(tweezer_configuration.amplitudes_y),
        np.array(tweezer_configuration.frequencies_y),
        np.array(tweezer_configuration.phases_y),
        NumberSamples(tweezer_configuration.number_samples),
    )
    return static_signal_x, static_signal_y


def move_segment_name(step: int) -> SegmentName:
    return SegmentName(f"Move segment {step}")


def rearrange_segment_name(step: int) -> SegmentName:
    return SegmentName(f"Rearrange segment {step}")


def static_segment_names(
    step: int,
) -> tuple[SegmentName, SegmentName]:
    return SegmentName(f"Static segment {step} integral part"), SegmentName(
        f"Static segment {step} fractional part"
    )


def static_step_names(
    step: int,
) -> tuple[StepName, StepName]:
    return StepName(f"Static step {step} integral part"), StepName(
        f"Static step {step} fractional part"
    )


def move_step_name(step: int) -> StepName:
    return StepName(f"Move step {step}")


def rearrange_step_name(step: int) -> StepName:
    return StepName(f"Rearrange step {step}")


def _get_segment_names(
    tweezer_sequence: Sequence[ArrangerInstruction],
) -> set[SegmentName]:
    segments = set[SegmentName]()
    for step, instruction in enumerate(tweezer_sequence):
        match instruction:
            case HoldTweezers():
                integral_part, fraction_part = static_segment_names(step)
                segments.add(integral_part)
                segments.add(fraction_part)
            case MoveTweezers():
                segments.add(move_segment_name(step))
            case RearrangeTweezers():
                segments.add(move_segment_name(step))
            case _:
                raise NotImplementedError
    # We add a segment for the last step to just loop over the last configuration
    integral_part, _ = static_segment_names(len(tweezer_sequence))
    segments.add(integral_part)
    return segments


def _get_next_step(
    current_step: int,
    tweezer_sequence: Sequence[ArrangerInstruction],
) -> StepName:
    if current_step == len(tweezer_sequence) - 1:
        return static_step_names(len(tweezer_sequence))[0]
    else:
        next_step_instruction = tweezer_sequence[current_step + 1]
        match next_step_instruction:
            case HoldTweezers():
                return static_step_names(current_step + 1)[0]
            case MoveTweezers():
                return move_step_name(current_step + 1)
            case RearrangeTweezers():
                return rearrange_step_name(current_step + 1)
            case _:
                raise NotImplementedError


def _get_steps(
    tweezer_sequence: Sequence[ArrangerInstruction],
) -> dict[StepName, StepConfiguration]:
    steps = dict[StepName, StepConfiguration]()
    for index, instruction in enumerate(tweezer_sequence):
        match instruction:
            case HoldTweezers():
                integral_step_part, fractional_step_part = static_step_names(index)
                integral_segment_part, fractional_segment_part = static_segment_names(
                    index
                )

                # Here the repetition is not correct, we'll need to update before starting the AWG sequence
                steps[integral_step_part] = StepConfiguration(
                    segment=integral_segment_part,
                    next_step=fractional_step_part,
                    repetition=1,
                )
                steps[fractional_step_part] = StepConfiguration(
                    segment=fractional_segment_part,
                    next_step=_get_next_step(index, tweezer_sequence),
                    repetition=1,
                )
            case MoveTweezers():
                steps[move_step_name(index)] = StepConfiguration(
                    segment=move_segment_name(index),
                    next_step=_get_next_step(index, tweezer_sequence),
                    repetition=1,
                )
            case RearrangeTweezers():
                steps[rearrange_step_name(index)] = StepConfiguration(
                    segment=rearrange_segment_name(index),
                    next_step=_get_next_step(index, tweezer_sequence),
                    repetition=1,
                )
            case _:
                raise NotImplementedError
    last_step = static_step_names(len(tweezer_sequence))[0]
    last_segment = static_segment_names(len(tweezer_sequence))[0]
    steps[last_step] = StepConfiguration(
        segment=last_segment,
        next_step=last_step,
        repetition=1,
    )
    return steps


_T = TypeVar("_T")


def first(iterable: Iterable[_T]) -> _T:
    return next(iter(iterable))


def number_ticks(start_time: float, stop_time: float, time_step: float) -> int:
    """Returns the number of ticks between start_time and stop_time.

    Args:
        start_time: The start time in seconds.
        stop_time: The stop time in seconds.
        time_step: The time step in seconds.
    """

    return stop_tick(stop_time, time_step) - start_tick(start_time, time_step)


def start_tick(start_time: float, time_step: float) -> int:
    """Returns the included first tick index of the step starting at start_time."""

    return math.ceil(start_time / time_step)


def stop_tick(stop_time: float, time_step: float) -> int:
    """Returns the excluded last tick index of the step ending at stop_time."""

    return math.ceil(stop_time / time_step)


def get_step_bounds(step_durations: Iterable[float]) -> list[tuple[float, float]]:
    """Returns the step bounds for the given step durations.

    For an iterable of step durations [d_0, d_1, ..., d_n], the step bounds are
    (0, d_0), (d_0, d_0 + d_1), ..., (d_0 + ... + d_{n-1}, d_0 + ... + d_n).
    """

    step_bounds = []
    start_time = 0.0
    for duration in step_durations:
        step_bounds.append((start_time, start_time + duration))
        start_time += duration
    return step_bounds
