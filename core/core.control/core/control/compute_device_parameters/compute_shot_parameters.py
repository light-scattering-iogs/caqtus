import logging
import math
from collections.abc import Mapping
from dataclasses import dataclass
from functools import singledispatch
from typing import Any, Optional

import numpy as np
from attrs import define, field

from core.configuration import Expression
from core.configuration.experiment import ExperimentConfig
from core.configuration.lane import (
    Lane,
    AnalogLane,
    Ramp,
    CameraLane,
    TakePicture,
    TweezerArrangerLane,
)
from core.configuration.sequence import ShotConfiguration
from core.device import DeviceName, DeviceParameter
from sequencer.channel import ChannelInstruction
from sequencer.configuration import (
    SequencerConfiguration,
    ChannelConfiguration,
    ExternalTriggerStart,
    ExternalClock,
    ExternalClockOnChange,
    Trigger,
    DigitalChannelConfiguration,
    AnalogChannelConfiguration,
)
from sequencer.instructions import ChannelLabel
from sequencer.instructions.struct_array_instruction import (
    SequencerInstruction,
    Pattern,
    Concatenate,
    Repeat,
)
from .camera_instruction import CameraInstruction
from .clock_instruction import ClockInstruction
from .compile_lane import (
    compile_lane,
    empty_channel_instruction,
    get_step_starts,
    compile_camera_instruction,
)
from .compile_steps import compile_step_durations
from .timing import number_ticks
from ..variable_namespace import VariableNamespace

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

ns = 1e-9


@dataclass
class StepProperties:
    name: str
    duration: float
    analog_times: Optional[np.ndarray] = None


def compute_shot_parameters(
    experiment_config: ExperimentConfig,
    shot_config: ShotConfiguration,
    variables: VariableNamespace,
) -> dict[DeviceName, dict[DeviceParameter, Any]]:
    """Compute the parameters to be applied to the devices before a shot."""

    return SequenceCompiler(
        experiment_config=experiment_config,
        shot_config=shot_config,
        variables=variables,
    ).compile()


@define
class SequenceCompiler:
    experiment_config: ExperimentConfig
    shot_config: ShotConfiguration
    variables: VariableNamespace

    step_durations: list[float] = field(init=False)
    step_bounds: list[float] = field(init=False)
    sequencer_configs: dict[DeviceName, SequencerConfiguration] = field(init=False)

    def __attrs_post_init__(self):
        self.step_durations = compile_step_durations(
            self.shot_config.step_names, self.shot_config.step_durations, self.variables
        )
        self.step_bounds = get_step_starts(self.step_durations)
        self.sequencer_configs = self.experiment_config.get_device_configs(
            SequencerConfiguration
        )

    def compile(self) -> dict[DeviceName, dict[DeviceParameter, Any]]:
        result: dict[DeviceName, dict[DeviceParameter, Any]] = {}

        camera_instructions = self.compute_camera_instructions()
        result |= get_camera_parameters(camera_instructions)

        result |= self.compile_sequencers_instructions(camera_instructions)

        result |= self.compute_tweezer_arranger_instructions()

        return result

    def compile_sequencers_instructions(
        self, camera_instructions: Mapping[DeviceName, CameraInstruction]
    ) -> dict[DeviceName, dict[DeviceParameter, Any]]:
        sequences: dict[DeviceName, SequencerInstruction] = {}
        for sequencer in get_sequencers_ordered_by_dependency():
            instructions = self.compile_sequencer_instructions(
                self.sequencer_configs[sequencer],
                camera_instructions,
                sequences,
            )
            sequences[sequencer] = convert_to_sequence(
                instructions, self.sequencer_configs[sequencer]
            )

        sequencer_parameters = {
            sequencer_name: {DeviceParameter("sequence"): sequence}
            for sequencer_name, sequence in sequences.items()
        }

        return sequencer_parameters

    def compile_sequencer_instructions(
        self,
        sequencer_config: SequencerConfiguration,
        camera_instructions: Mapping[DeviceName, CameraInstruction],
        sequences: Mapping[DeviceName, SequencerInstruction],
    ) -> dict[ChannelLabel, SequencerInstruction]:
        instructions: dict[ChannelLabel, SequencerInstruction] = {}

        for channel_number, channel in enumerate(sequencer_config.channels):
            instructions[
                ChannelLabel(channel_number)
            ] = self.compile_channel_instruction(
                channel,
                sequencer_config,
                camera_instructions,
                sequences,
            )
        max_delay = round_to_ns(sequencer_config.get_maximum_delay())
        for channel_number, channel in enumerate(sequencer_config.channels):
            delay = round_to_ns(channel.delay)
            instruction = instructions[ChannelLabel(channel_number)]
            pre_step = Pattern([instruction[0]]) * delay
            post_step = Pattern([instruction[-1]]) * (max_delay - delay)
            instructions[ChannelLabel(channel_number)] = (
                pre_step + instruction + post_step
            )

        return instructions

    def compute_camera_instructions(self) -> dict[DeviceName, CameraInstruction]:
        """Compute the parameters to be applied to each camera.

        Returns:
            A dictionary mapping camera names to their parameters
        """

        step_durations = self.step_durations

        step_bounds = self.step_bounds

        result = {}
        shot_duration = sum(step_durations)

        camera_lanes = self.shot_config.get_lanes(CameraLane)
        for lane_name, lane in camera_lanes.items():
            triggers = []
            for value, start, stop in lane.get_value_spans():
                if isinstance(value, TakePicture):
                    state = True
                else:
                    state = False
                duration = sum(step_durations[start:stop])
                triggers.append(
                    (state, step_bounds[start], step_bounds[stop], duration)
                )
            instructions = CameraInstruction(
                timeout=shot_duration
                + 1,  # add a second to be safe and not timeout too early if the shot takes time to start
                triggers=triggers,
            )
            result[DeviceName(lane_name)] = instructions
        return result

    def compute_tweezer_arranger_instructions(
        self,
    ) -> dict[DeviceName, dict[DeviceParameter, Any]]:
        step_bounds = self.step_bounds

        result = {}

        tweezer_arranger_lanes = self.shot_config.get_lanes(TweezerArrangerLane)
        for lane_name, lane in tweezer_arranger_lanes.items():
            durations = []
            for _, start, stop in lane.get_value_spans():
                durations.append(step_bounds[stop] - step_bounds[start])
            result[DeviceName(lane_name)] = {
                DeviceParameter("tweezer_sequence_durations"): durations
            }
        return result

    def compile_channel_instruction(
        self,
        channel: ChannelConfiguration,
        sequencer_config: SequencerConfiguration,
        camera_instructions: Mapping[DeviceName, CameraInstruction],
        sequences: Mapping[DeviceName, SequencerInstruction],
    ) -> SequencerInstruction:
        if channel.has_special_purpose():
            target = DeviceName(str(channel.description))
            if target in camera_instructions:
                instruction = compile_camera_instruction(
                    camera_instructions[target], sequencer_config.time_step
                )
            elif target in sequences:
                length = number_ticks(
                    self.step_bounds[0],
                    self.step_bounds[-1],
                    sequencer_config.time_step * ns,
                )

                instruction = compile_clock_instruction(
                    sequences[target],
                    self.sequencer_configs[target].time_step,
                    sequencer_config.time_step,
                    length,
                    self.sequencer_configs[target].trigger,
                )
            elif channel.is_unused():
                instruction = empty_channel_instruction(
                    channel.default_value,
                    self.step_durations,
                    sequencer_config.time_step,
                )
            else:
                instruction = empty_channel_instruction(
                    channel.default_value,
                    self.step_durations,
                    sequencer_config.time_step,
                )
        else:
            if lane := self.shot_config.find_lane(channel.description):
                instruction = compile_lane(
                    lane,
                    self.step_durations,
                    sequencer_config.time_step,
                    self.variables,
                )
            else:
                instruction = empty_channel_instruction(
                    channel.default_value,
                    self.step_durations,
                    sequencer_config.time_step,
                )

        instruction = instruction.apply(channel.output_mapping.convert)
        return instruction


def get_sequencers_ordered_by_dependency() -> list[DeviceName]:
    return [
        DeviceName("NI6738 card"),
        DeviceName("Swabian pulse streamer"),
        DeviceName("Spincore PulseBlaster sequencer"),
    ]


def round_to_ns(value: float) -> int:
    ns = 1e-9
    return round(value / ns)


def compile_clock_instruction(
    target_sequence: SequencerInstruction,
    target_time_step: int,
    base_time_step: int,
    sequence_length: int,
    trigger: Trigger,
) -> SequencerInstruction:
    if isinstance(trigger, ExternalTriggerStart):
        clock_single_pulse = Pattern([True]) * 10
        instruction = clock_single_pulse + Pattern([False]) * (
            sequence_length - len(clock_single_pulse)
        )
    elif isinstance(trigger, ExternalClock):
        multiplier, high, low = high_low_clicks(target_time_step, base_time_step)
        clock_single_pulse = Pattern([True]) * high + Pattern([False]) * low
        instruction = clock_single_pulse * (sequence_length // multiplier)
        instruction = instruction + Pattern([False]) * (
            sequence_length - len(instruction)
        )
    elif isinstance(trigger, ExternalClockOnChange):
        multiplier, high, low = high_low_clicks(target_time_step, base_time_step)
        clock_single_pulse = Pattern([True]) * high + Pattern([False]) * low
        instruction = get_adaptive_clock(target_sequence, clock_single_pulse)[
            :sequence_length
        ]
    else:
        raise NotImplementedError(f"Trigger {trigger} not implemented")
    return instruction


@singledispatch
def get_adaptive_clock(
    target_sequence: SequencerInstruction, clock_pulse: SequencerInstruction
) -> SequencerInstruction:
    raise NotImplementedError(f"Target sequence {target_sequence} not implemented")


@get_adaptive_clock.register
def _(
    target_sequence: Pattern, clock_pulse: SequencerInstruction
) -> SequencerInstruction:
    return clock_pulse * len(target_sequence)


@get_adaptive_clock.register
def _(
    target_sequence: Concatenate, clock_pulse: SequencerInstruction
) -> SequencerInstruction:
    return SequencerInstruction.join(
        *(
            get_adaptive_clock(sequence, clock_pulse)
            for sequence in target_sequence.instructions
        )
    )


@get_adaptive_clock.register
def _(
    target_sequence: Repeat, clock_pulse: SequencerInstruction
) -> SequencerInstruction:
    if len(target_sequence.instruction) == 1:
        return clock_pulse + Pattern([False]) * (
            (len(target_sequence) - 1) * len(clock_pulse)
        )
    else:
        raise NotImplementedError(
            "Only one instruction is supported in a repeat block at the moment"
        )


def high_low_clicks(
    clock_time_step: int, sequencer_time_step: int
) -> tuple[int, int, int]:
    """Return the number of steps the sequencer must be high then low to produce a clock pulse."""
    if not clock_time_step >= 2 * sequencer_time_step:
        raise ValueError(
            "Clock time step must be at least twice the sequencer time step"
        )
    div, mod = divmod(clock_time_step, sequencer_time_step)
    if not mod == 0:
        logger.debug(f"{clock_time_step=}, {sequencer_time_step=}, {div=}, {mod=}")
        raise ValueError(
            "Clock time step must be an integer multiple of the sequencer time step"
        )
    if div % 2 == 0:
        return div, div // 2, div // 2
    else:
        return div, div // 2 + 1, div // 2


def convert_to_sequence(
    channel_instructions: dict[ChannelLabel, SequencerInstruction],
    sequencer_config: SequencerConfiguration,
) -> SequencerInstruction:
    converted_instructions = {}
    channel_types = sequencer_config.channel_types()
    for channel, channel_type in enumerate(channel_types):
        if issubclass(channel_type, DigitalChannelConfiguration):
            converted_instructions[ChannelLabel(channel)] = channel_instructions[
                ChannelLabel(channel)
            ].as_type(np.dtype([(f"ch {channel}", bool)]))
        elif issubclass(channel_type, AnalogChannelConfiguration):
            converted_instructions[ChannelLabel(channel)] = channel_instructions[
                ChannelLabel(channel)
            ].as_type(np.dtype([(f"ch {channel}", float)]))
        else:
            raise NotImplementedError

    channel_label = ChannelLabel(0)
    sequence = converted_instructions[channel_label]
    for channel_index in range(1, sequencer_config.number_channels):
        channel_label = ChannelLabel(channel_index)
        sequence = sequence.merge_channels(converted_instructions[channel_label])
    return sequence


def get_camera_parameters(
    camera_instructions: Mapping[DeviceName, CameraInstruction]
) -> dict[DeviceName, dict[DeviceParameter, Any]]:
    """Extract the parameters to be applied to each camera from the instructions.

    This function only keeps the parameters to be applied to a camera. It removes the triggers because they will be used
    to program a digital sequencer and not the cameras themselves.

    Returns:
        A dictionary mapping camera names to their parameters
    """

    result = {}

    for camera, instruction in camera_instructions.items():
        exposures = [
            duration for expose, start, stop, duration in instruction.triggers if expose
        ]
        result[camera] = {
            DeviceParameter("timeout"): instruction.timeout,
            DeviceParameter("exposures"): exposures,
        }

    return result


def compile_clock_requirements(
    sequencer_configs: Mapping[DeviceName, SequencerConfiguration],
    shot_config: ShotConfiguration,
    variables: VariableNamespace,
) -> dict[DeviceName, list[ClockInstruction]]:
    # TODO: make this more general to more devices.

    step_durations = compile_step_durations(
        shot_config.step_names, shot_config.step_durations, variables
    )
    step_bounds = get_step_starts(step_durations)

    sequencer = DeviceName("NI6738 card")
    sequencer_config = sequencer_configs[sequencer]
    sequencer_clock_instructions = []
    for step_index, clock_instruction in enumerate(
        compute_clock_step_requirements(
            sequencer_config,
            shot_config,
        )
    ):
        sequencer_clock_instructions.append(
            ClockInstruction(
                start=step_bounds[step_index],
                stop=step_bounds[step_index + 1],
                time_step=sequencer_config.time_step,
                order=clock_instruction,
            )
        )
    arranger = DeviceName("Tweezer Arranger")
    arranger_clock_instructions = [
        ClockInstruction(
            start=step_bounds[0],
            stop=step_bounds[-1],
            time_step=1000,
            order=ClockInstruction.StepInstruction.TriggerStart,
        )
    ]

    pulse_streamer = DeviceName("Swabian pulse streamer")
    pulse_streamer_clock_instructions = [
        ClockInstruction(
            start=step_bounds[0],
            stop=step_bounds[-1],
            time_step=1000,
            order=ClockInstruction.StepInstruction.TriggerStart,
        )
    ]

    return {
        sequencer: sequencer_clock_instructions,
        arranger: arranger_clock_instructions,
        pulse_streamer: pulse_streamer_clock_instructions,
    }


def compute_clock_step_requirements(
    sequencer_config: SequencerConfiguration,
    shot_config: ShotConfiguration,
) -> list[ClockInstruction.StepInstruction]:
    lanes = {
        channel.description: lane
        for channel in sequencer_config.get_lane_channels()
        if (lane := shot_config.find_lane(channel.description))
    }

    result = []
    for step in range(shot_config.number_steps):
        instruction = ClockInstruction.StepInstruction.NoClock
        for lane in lanes.values():
            if is_constant(lane, step):
                instruction = ClockInstruction.StepInstruction.TriggerStart
            else:
                result.append(ClockInstruction.StepInstruction.Clock)
                break
        else:
            result.append(instruction)
    return result


def start_tick(time: float, time_step: float) -> int:
    return math.ceil(time / time_step)


def get_constant_steps(
    shot_config: ShotConfiguration,
    sequencer_config: SequencerConfiguration,
) -> list[bool]:
    lanes = {
        channel.description: lane
        for channel in sequencer_config.get_lane_channels()
        if (lane := shot_config.find_lane(channel.description))
    }

    result = []
    for step in range(shot_config.number_steps):
        result.append(all(is_constant(lane, step) for lane in lanes.values()))
    return result


def is_constant(lane: Lane, step: int) -> bool:
    if isinstance(lane, AnalogLane):
        value = lane.get_effective_value(step)
        if isinstance(value, Ramp):
            return False
        elif isinstance(value, Expression):
            return is_expression_constant(value)
    else:
        raise NotImplementedError("Not expecting a non analog lane here.")


def is_expression_constant(expression: Expression) -> bool:
    return "t" not in expression.upstream_variables
