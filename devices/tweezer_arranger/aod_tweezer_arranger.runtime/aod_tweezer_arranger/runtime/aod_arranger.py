import logging
import math
from typing import Sequence, Mapping, Literal, TypeVar, Iterable

import numpy as np
from attr import frozen
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
    HoldTweezers,
    MoveTweezers,
    RearrangeTweezers,
    ArrangerInstruction,
)
from tweezer_arranger.configuration import (
    TweezerConfigurationName,
)
from tweezer_arranger.runtime import TweezerArranger, RearrangementFailedError
from .signal_generator import SignalGenerator, NumberSamples, AWGSignalArray

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

BYPASS_POWER_CHECK = True


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
    _signal_generator: SignalGenerator
    _static_signals: dict[TweezerConfigurationName, SegmentData] = {}
    _tweezer_sequence_bounds: tuple[tuple[float, float], ...] = ()
    _step_number_ticks: list[int]

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
            if config.number_samples != first_config.number_samples:
                raise ValueError(
                    "All static tweezer configurations must have the same number of samples"
                )
        return configurations

    @log_exception(logger)
    def initialize(self) -> None:
        super().initialize()
        self._step_number_ticks = [0] * len(self.tweezer_sequence)
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
            first_step=static_step_names(0).integer,
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
                static_segment = static_segment_names(step).integer
                segment_data[static_segment] = self._static_signals[
                    instruction.tweezer_configuration
                ]
        last_segment = static_segment_names(len(self.tweezer_sequence)).integer
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

    @property
    def number_samples_per_loop(self) -> int:
        first_config = first(self.tweezer_configurations.values())
        return first_config.number_samples

    @log_exception(logger)
    def update_parameters(self, *, tweezer_sequence_durations: Sequence[float]) -> None:
        with DurationTimerLog(logger, "Updating awg parameters"):
            if not len(tweezer_sequence_durations) == len(self.tweezer_sequence):
                raise ValueError(
                    "tweezer_sequence_durations must be the same length as tweezer_sequence"
                )
            self._tweezer_sequence_bounds = tuple(
                get_step_bounds(tweezer_sequence_durations)
            )
            # this is a limitation of the AWG that each segment must have a length
            # that is a multiple of 32.
            time_step = 32 / self.sampling_rate
            step_repetitions = dict[StepName, int]()
            segment_data: dict[SegmentName, SegmentData] = {}
            number_samples_per_loop = self.number_samples_per_loop
            for step, (instruction, (start, stop)) in enumerate(
                zip(self.tweezer_sequence, self._tweezer_sequence_bounds)
            ):
                integer_start = (
                    start_tick(start, number_samples_per_loop / self.sampling_rate)
                    * number_samples_per_loop
                )
                integer_stop = (
                    stop_tick(stop, number_samples_per_loop / self.sampling_rate)
                    * number_samples_per_loop
                )
                before_start = start_tick(start, time_step) * 32
                after_stop = stop_tick(stop, time_step) * 32

                ticks = after_stop - before_start
                self._step_number_ticks[step] = ticks
                if isinstance(instruction, HoldTweezers):
                    integer_repetitions = (
                        integer_stop - integer_start
                    ) // self.number_samples_per_loop
                    step_repetitions[
                        static_step_names(step).integer
                    ] = integer_repetitions
                    segment_data[
                        static_segment_names(step).before
                    ] = self._static_signals[instruction.tweezer_configuration][
                        :, before_start % number_samples_per_loop :
                    ]
                    segment_data[
                        static_segment_names(step).after
                    ] = self._static_signals[instruction.tweezer_configuration][
                        :, : after_stop % number_samples_per_loop
                    ]
                elif isinstance(instruction, MoveTweezers):
                    number_samples = NumberSamples(after_stop - before_start)
                    previous_config = self.tweezer_configurations[
                        instruction.initial_tweezer_configuration
                    ]
                    next_config = self.tweezer_configurations[
                        instruction.final_tweezer_configuration
                    ]

                    previous_step_stop = (
                        stop_tick(self._tweezer_sequence_bounds[step - 1][1], time_step)
                        * 32
                    )
                    next_step_start = (
                        start_tick(
                            self._tweezer_sequence_bounds[step + 1][0], time_step
                        )
                        * 32
                    )

                    move_signal_x = self._signal_generator.generate_signal_moving_traps(
                        previous_config.amplitudes_x,
                        next_config.amplitudes_x,
                        previous_config.frequencies_x,
                        next_config.frequencies_x,
                        previous_config.phases_x,
                        next_config.phases_x,
                        number_samples,
                        previous_step_stop % self.number_samples_per_loop,
                        next_step_start % self.number_samples_per_loop,
                    )
                    move_signal_y = self._signal_generator.generate_signal_moving_traps(
                        previous_config.amplitudes_y,
                        next_config.amplitudes_y,
                        previous_config.frequencies_y,
                        next_config.frequencies_y,
                        previous_config.phases_y,
                        next_config.phases_y,
                        number_samples,
                        previous_step_stop % self.number_samples_per_loop,
                        next_step_start % self.number_samples_per_loop,
                    )
                    segment_data[move_segment_name(step)] = np.array(
                        (move_signal_x, move_signal_y), dtype=np.int16
                    )
                elif isinstance(instruction, RearrangeTweezers):
                    segment_data[rearrange_segment_name(step)] = np.zeros(
                        (2, ticks), dtype=np.int16
                    )
                else:
                    raise ValueError(f"Unknown instruction {instruction}")
            del segment_data[static_segment_names(0).before]
            self._awg.update_parameters(
                segment_data=segment_data,
                step_repetitions=step_repetitions,
                bypass_power_check=BYPASS_POWER_CHECK,
            )

    @log_exception(logger)
    def prepare_rearrangement(
        self, *, step: int, atom_present: Mapping[tuple[int, int], bool]
    ) -> None:
        with DurationTimerLog(logger, "Preparing rearrangement"):
            previous_instruction = self.tweezer_sequence[step - 1]
            if not isinstance(previous_instruction, HoldTweezers):
                raise ValueError(f"Instruction at step {step - 1} must be HoldTweezers")

            rearrange_instruction = self.tweezer_sequence[step]
            if not isinstance(rearrange_instruction, RearrangeTweezers):
                raise ValueError(
                    f"Instruction at step {step} must be RearrangeTweezers"
                )
            initial_config = self.tweezer_configurations[
                rearrange_instruction.initial_tweezer_configuration
            ]
            final_config = self.tweezer_configurations[
                rearrange_instruction.final_tweezer_configuration
            ]

            if not initial_config.number_tweezers_along_y == 1:
                raise ValueError(
                    f"Can only rearrange atoms if all atoms are in the same row"
                )
            if not final_config.number_tweezers_along_y == 1:
                raise ValueError(
                    f"Can only rearrange atoms if all atoms are in the same row"
                )

            atoms_before = [False] * initial_config.number_tweezers_along_x

            for (x, y), present in atom_present.items():
                if y != 0:
                    raise ValueError(
                        f"Can only rearrange atoms if they all are on the x-axis"
                    )
                if x >= initial_config.number_tweezers_along_x:
                    raise ValueError(
                        f"Atom present at ({x}, {y}) but there are only "
                        f"{initial_config.number_tweezers_along_x} tweezers along x"
                    )
                else:
                    atoms_before[x] = present

            moves = compute_moves_1d(
                atoms_before,
                final_config.number_tweezers_along_x,
                shift_towards="high",
            )

            initial_indices = [before for before, after in moves.items()]
            final_indices = [after for before, after in moves.items()]

            time_step = 32 / self.sampling_rate
            number_samples = NumberSamples(
                number_ticks(
                    self._tweezer_sequence_bounds[step][0],
                    self._tweezer_sequence_bounds[step][1],
                    time_step,
                )
                * 32
            )

            previous_step_stop = (
                stop_tick(self._tweezer_sequence_bounds[step - 1][1], time_step) * 32
            )
            next_step_start = (
                start_tick(self._tweezer_sequence_bounds[step + 1][0], time_step) * 32
            )
            move_signal_x = self._signal_generator.generate_signal_moving_traps(
                np.array(initial_config.amplitudes_x)[initial_indices],
                np.array(final_config.amplitudes_x)[final_indices],
                np.array(initial_config.frequencies_x)[initial_indices],
                np.array(final_config.frequencies_x)[final_indices],
                np.array(initial_config.phases_x)[initial_indices],
                np.array(final_config.phases_x)[final_indices],
                number_samples,
                previous_step_stop % self.number_samples_per_loop,
                next_step_start % self.number_samples_per_loop,
            )
            move_signal_y = self._signal_generator.generate_signal_moving_traps(
                initial_config.amplitudes_y,
                final_config.amplitudes_y,
                initial_config.frequencies_y,
                final_config.frequencies_y,
                initial_config.phases_y,
                final_config.phases_y,
                number_samples,
                previous_step_stop % self.number_samples_per_loop,
                next_step_start % self.number_samples_per_loop,
            )
            segment_data = {
                rearrange_segment_name(step): np.array((move_signal_x, move_signal_y))
            }

            self._awg.update_parameters(
                segment_data=segment_data,
                bypass_power_check=BYPASS_POWER_CHECK,
            )
            current_step = self._awg.get_current_step()
            previous_steps = find_steps_before(
                rearrange_step_name(step),
                _get_steps(self.tweezer_sequence),
                static_step_names(0).integer,
            )
            if current_step not in previous_steps:
                raise RearrangementFailedError(
                    f"AWG is not in the correct step. "
                    f"Expected one of {previous_steps} but is {current_step}"
                )
            self._awg.save_segments_data()

    def start_sequence(self) -> None:
        self._awg.stop_sequence()
        self._awg.start_sequence(external_trigger=True)

    def has_sequence_finished(self) -> bool:
        current_step = self._awg.get_current_step()
        logger.debug(f"Current step: {current_step}")
        return current_step == static_step_names(len(self.tweezer_sequence)).integer

    @classmethod
    def exposed_remote_methods(cls) -> tuple[str, ...]:
        return super().exposed_remote_methods() + (
            "start_sequence",
            "has_sequence_finished",
            "prepare_rearrangement",
        )


def compute_moves_1d(
    atoms_before: Sequence[bool],
    number_target_traps: int,
    shift_towards: Literal["low", "high"] = "low",
) -> dict[int, int]:
    """
    Compute the moves for a rearrangement in 1D.

    Args:
        atoms_before: Indicated which traps are filled, i.e. atoms_before[i] is True if the trap with index i is filled
            and False otherwise.
        number_target_traps: The number of traps available for the rearrangement. This is the number of traps that could
            be filled after the rearrangement if there was no limit on the number of atoms.
        shift_towards: Whether to shift the atoms towards the low or high index traps.

    Returns:
        moves: A dictionary where moves[i] is the trap index that the atom at index i should be moved to.
    """

    initial_indices = [i for i, filled in enumerate(atoms_before) if filled]

    target_indices = [i for i, _ in enumerate(initial_indices) if i < 20]
    if shift_towards == "low":
        pass
    elif shift_towards == "high":
        target_indices = [
            i + number_target_traps - len(target_indices) for i in target_indices
        ]
    else:
        raise ValueError(f"Invalid shift_towards: {shift_towards}")

    return dict(zip(initial_indices, target_indices))


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


@frozen
class InstructionSegmentNames:
    before: SegmentName
    integer: SegmentName
    after: SegmentName


def static_segment_names(
    step: int,
) -> InstructionSegmentNames:
    return InstructionSegmentNames(
        before=SegmentName(f"Static segment {step} before part"),
        integer=SegmentName(f"Static segment {step} integer part"),
        after=SegmentName(f"Static segment {step} after part"),
    )


@frozen
class HoldInstructionStepNames:
    before: StepName
    integer: StepName
    after: StepName


def static_step_names(
    step: int,
) -> HoldInstructionStepNames:
    return HoldInstructionStepNames(
        before=StepName(f"Static step {step} before part"),
        integer=StepName(f"Static step {step} integer part"),
        after=StepName(f"Static step {step} after part"),
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
                segment_names = static_segment_names(step)
                segments.add(segment_names.before)
                segments.add(segment_names.integer)
                segments.add(segment_names.after)
            case MoveTweezers():
                segments.add(move_segment_name(step))
            case RearrangeTweezers():
                segments.add(rearrange_segment_name(step))
            case _:
                raise NotImplementedError
    # We add a segment for the last step to just loop over the last configuration
    integral_part = static_segment_names(len(tweezer_sequence)).integer
    segments.add(integral_part)
    segments.remove(static_segment_names(0).before)
    return segments


def _get_next_step(
    current_step: int,
    tweezer_sequence: Sequence[ArrangerInstruction],
) -> StepName:
    if current_step == len(tweezer_sequence) - 1:
        return static_step_names(len(tweezer_sequence)).integer
    else:
        next_step_instruction = tweezer_sequence[current_step + 1]
        match next_step_instruction:
            case HoldTweezers():
                return static_step_names(current_step + 1).before
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
                instruction_step_names = static_step_names(index)
                instruction_segment_names = static_segment_names(index)

                steps[instruction_step_names.before] = StepConfiguration(
                    segment=instruction_segment_names.before,
                    next_step=instruction_step_names.integer,
                    repetition=1,
                )
                # Below, the repetition is not correct, we'll need to update before starting the AWG sequence
                steps[instruction_step_names.integer] = StepConfiguration(
                    segment=instruction_segment_names.integer,
                    next_step=instruction_step_names.after,
                    repetition=1,
                )
                steps[instruction_step_names.after] = StepConfiguration(
                    segment=instruction_segment_names.after,
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
    last_step = static_step_names(len(tweezer_sequence)).integer
    last_segment = static_segment_names(len(tweezer_sequence)).integer
    steps[last_step] = StepConfiguration(
        segment=last_segment,
        next_step=last_step,
        repetition=1,
    )
    del steps[static_step_names(0).before]
    return steps


def find_steps_before(
    step: StepName,
    steps: dict[StepName, StepConfiguration],
    initial_step: StepName,
) -> list[StepName]:
    result = list[StepName]()
    current_step = initial_step
    while current_step != step:
        result.append(current_step)
        current_step = steps[current_step].next_step
    return result


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
