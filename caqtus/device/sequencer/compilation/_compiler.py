import functools
from typing import Mapping, Any

import numpy as np

import caqtus.formatter as fmt
from caqtus.device import DeviceName, DeviceParameter
from caqtus.shot_compilation import SequenceContext, ShotContext
from caqtus.shot_compilation.lane_compilers.timing import number_ticks, ns
from caqtus.types.recoverable_exceptions import InvalidValueError
from caqtus.types.units import Unit, InvalidDimensionalityError, dimensionless
from caqtus.types.units.base import base_units
from caqtus.types.variable_name import DottedVariableName
from ._trigger_compiler import TriggerCompiler
from ..channel_commands import DimensionedSeries
from ..configuration import (
    SequencerConfiguration,
    ChannelConfiguration,
    DigitalChannelConfiguration,
    AnalogChannelConfiguration,
)
from ..instructions import (
    with_name,
    stack_instructions,
    SequencerInstruction,
    Pattern,
    Ramp,
    Concatenated,
    concatenate,
    Repeated,
)
from ..trigger import ExternalClockOnChange, ExternalTriggerStart, SoftwareTrigger


class SequencerCompiler(TriggerCompiler):
    def __init__(self, device_name: DeviceName, sequence_context: SequenceContext):
        super().__init__(device_name, sequence_context)
        configuration = sequence_context.get_device_configuration(device_name)
        if not isinstance(configuration, SequencerConfiguration):
            raise TypeError(
                f"Expected a sequencer configuration for device {device_name}, got "
                f"{type(configuration)}"
            )
        self.__configuration = configuration
        self.__device_name = device_name

    def compile_initialization_parameters(self) -> Mapping[DeviceParameter, Any]:
        # TODO: raise DeviceNotUsedException if the sequencer is not used for the
        #  current sequence
        return {
            DeviceParameter("time_step"): self.__configuration.time_step,
            DeviceParameter("trigger"): self.__configuration.trigger,
        }

    def compile_shot_parameters(
        self,
        shot_context: ShotContext,
    ) -> Mapping[str, Any]:
        """Evaluates the output for each channel of the sequencer."""

        max_advance, max_delay = self._find_max_advance_and_delays(
            shot_context.get_variables()
        )

        channel_instructions = []
        exceptions = []
        for channel_number, channel in enumerate(self.__configuration.channels):
            try:
                output_series = channel.output.evaluate(
                    self.__configuration.time_step,
                    max_advance,
                    max_delay,
                    shot_context,
                )
                instruction = _convert_series_to_instruction(output_series, channel)
                channel_instructions.append(
                    with_name(instruction, f"ch {channel_number}")
                )
            except Exception as e:
                channel_error = ChannelCompilationError(
                    f"Error occurred when evaluating output for channel "
                    f"{channel_number} ({channel})"
                )
                channel_error.__cause__ = e
                exceptions.append(channel_error)
        if exceptions:
            raise SequencerCompilationError(
                f"Errors occurred when evaluating outputs for "
                f"{fmt.device(self.__device_name)}",
                exceptions,
            )
        stacked = stack_instructions(*channel_instructions)
        return {"sequence": stacked}

    def _find_max_advance_and_delays(
        self, variables: Mapping[DottedVariableName, Any]
    ) -> tuple[int, int]:
        advances_and_delays = [
            channel.output.evaluate_max_advance_and_delay(
                self.__configuration.time_step, variables
            )
            for channel in self.__configuration.channels
        ]
        advances, delays = zip(*advances_and_delays)
        return max(advances), max(delays)

    def compute_trigger(
        self, sequencer_time_step: int, shot_context: ShotContext
    ) -> SequencerInstruction[np.bool_]:
        length = number_ticks(
            0, shot_context.get_shot_duration(), sequencer_time_step * ns
        )

        if isinstance(self.__configuration.trigger, ExternalClockOnChange):
            single_clock_pulse = get_master_clock_pulse(
                self.__configuration.time_step, sequencer_time_step
            )
            slave_parameters = shot_context.get_shot_parameters(self.__device_name)
            slave_instruction = slave_parameters["sequence"]
            instruction = get_adaptive_clock(slave_instruction, single_clock_pulse)[
                :length
            ]
            return instruction
        elif isinstance(self.__configuration.trigger, ExternalTriggerStart):
            return super().compute_trigger(sequencer_time_step, shot_context)
        elif isinstance(self.__configuration.trigger, SoftwareTrigger):
            raise InvalidValueError(
                "Can't generate a trigger for a sequencer that is software triggered"
            )
        else:
            raise NotImplementedError(
                f"Can't generate trigger for {self.__configuration.trigger}"
            )


def get_master_clock_pulse(
    slave_time_step: int, master_time_step: int
) -> SequencerInstruction[np.bool_]:
    _, high, low = high_low_clicks(slave_time_step, master_time_step)
    single_clock_pulse = Pattern([True]) * high + Pattern([False]) * low
    assert len(single_clock_pulse) * master_time_step == slave_time_step
    return single_clock_pulse


def high_low_clicks(slave_time_step: int, master_timestep: int) -> tuple[int, int, int]:
    """Return the number of steps the master sequencer must be high then low to
    produce a clock pulse for the slave sequencer.

    Returns:
        A tuple with its first element being the number of master steps that constitute
        a full slave clock cycle, the second element being the number of master steps
        for which the master must be high and the third element being the number of
        master steps for which the master must be low.
        The first element is the sum of the second and third elements.
    """

    if not slave_time_step >= 2 * master_timestep:
        raise ValueError(
            "Slave time step must be at least twice the master sequencer time step"
        )
    div, mod = divmod(slave_time_step, master_timestep)
    if not mod == 0:
        raise ValueError(
            "Slave time step must be an integer multiple of the master sequencer time "
            "step"
        )
    if div % 2 == 0:
        return div, div // 2, div // 2
    else:
        return div, div // 2 + 1, div // 2


@functools.singledispatch
def get_adaptive_clock(
    slave_instruction: SequencerInstruction, clock_pulse: SequencerInstruction
) -> SequencerInstruction:
    """Generates a clock signal for a slave instruction."""

    raise NotImplementedError(
        f"Don't know how to generate a clock for an instruction of type "
        f"{type(slave_instruction)}"
    )


@get_adaptive_clock.register
def _(
    target_sequence: Pattern | Ramp, clock_pulse: SequencerInstruction
) -> SequencerInstruction:
    return clock_pulse * len(target_sequence)


@get_adaptive_clock.register
def _(
    target_sequence: Concatenated, clock_pulse: SequencerInstruction
) -> SequencerInstruction:
    return concatenate(
        *(
            get_adaptive_clock(sequence, clock_pulse)
            for sequence in target_sequence.instructions
        )
    )


@get_adaptive_clock.register
def _(
    target_sequence: Repeated, clock_pulse: SequencerInstruction
) -> SequencerInstruction:
    if len(target_sequence.instruction) == 1:
        return clock_pulse + Pattern([False]) * (
            (len(target_sequence) - 1) * len(clock_pulse)
        )
    else:
        raise NotImplementedError(
            "Only one instruction is supported in a repeat block at the moment"
        )


class SequencerCompilationError(ExceptionGroup):
    pass


class ChannelCompilationError(Exception):
    pass


def _convert_series_to_instruction(
    series: DimensionedSeries, channel: ChannelConfiguration
) -> SequencerInstruction:
    if isinstance(channel, DigitalChannelConfiguration):
        if series.units is not None:
            raise InvalidDimensionalityError(
                f"Digital channel {channel} output has units {series.units}, expected "
                "no units"
            )
        instruction = series.values.as_type(np.dtype(np.bool_))
    elif isinstance(channel, AnalogChannelConfiguration):
        required_unit = Unit(channel.output_unit)
        if required_unit == dimensionless:
            if series.units is not None:
                raise InvalidDimensionalityError(
                    f"Analog channel {channel} output has units {series.units}, "
                    f"expected dimensionless"
                )
            instruction = series.values.as_type(np.dtype(np.float64))
        else:
            required_base_units = base_units(required_unit)
            if series.units != required_base_units:
                raise InvalidDimensionalityError(
                    f"Analog channel {channel} output has units {series.units}, "
                    f"expected {required_base_units}"
                )
            instruction = series.values.as_type(np.dtype(np.float64))
    else:
        raise TypeError(f"Unknown channel type {type(channel)}")

    return instruction
