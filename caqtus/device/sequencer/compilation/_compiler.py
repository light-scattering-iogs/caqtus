import functools
from collections.abc import Iterable
from typing import Mapping, Any, Optional, TypedDict

import attrs
import numpy as np

# TODO: Can remove tblib support once the experiment manager runs in a single process
import tblib.pickling_support

from caqtus.device import DeviceName
from caqtus.shot_compilation import SequenceContext, ShotContext
from caqtus.shot_compilation.lane_compilers.timing import number_time_steps
from caqtus.types.recoverable_exceptions import InvalidValueError
from caqtus.types.units import Unit, InvalidDimensionalityError, dimensionless
from caqtus.types.units.base import is_in_base_units, base_units
from caqtus.types.variable_name import DottedVariableName
from .._time_step import TimeStep
from ..channel_commands import ChannelOutput
from ..channel_commands import DimensionedSeries
from ..channel_commands._channel_sources._trigger_compiler import (
    TriggerableDeviceCompiler,
)
from ..configuration import DigitalChannelConfiguration, AnalogChannelConfiguration
from ..configuration import (
    SequencerConfiguration,
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
from ..trigger import (
    ExternalClockOnChange,
    ExternalTriggerStart,
    SoftwareTrigger,
    Trigger,
)


class SequencerCompiler(TriggerableDeviceCompiler):
    """Compile parameters for a sequencer device."""

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

    class SequencerInitializationParameters(TypedDict):
        """The parameters to pass to the sequencer constructor.

        Fields:
            time_step: The time step of the sequencer.
            trigger: The trigger configuration of the sequencer.
        """

        time_step: TimeStep
        trigger: Trigger

    def compile_initialization_parameters(self) -> SequencerInitializationParameters:
        """Compile the parameters needed to initialize the sequencer.

        Returns:
            A dictionary with the following keys:

            * 'time_step': The time step of the sequencer, in ns.
            * 'trigger': The trigger configuration of the sequencer.
        """

        # TODO: raise DeviceNotUsedException if the sequencer is not used for the
        #  current sequence
        return self.SequencerInitializationParameters(
            time_step=self.__configuration.time_step,
            trigger=self.__configuration.trigger,
        )

    class SequencerShotParameters(TypedDict):
        """The parameters to pass to the sequencer controller for a shot.

        Fields:
            sequence: The instructions to execute on the sequencer.
        """

        sequence: SequencerInstruction

    def compile_shot_parameters(
        self,
        shot_context: ShotContext,
    ) -> SequencerShotParameters:
        """Evaluates the output for each channel of the sequencer."""

        instructions = {}

        for channel_index, channel in enumerate(self.__configuration.channels):
            output = channel.output
            if isinstance(channel, DigitalChannelConfiguration):
                dtype = np.dtype(np.bool_)
                units = None
            elif isinstance(channel, AnalogChannelConfiguration):
                dtype = np.dtype(np.float64)
                units = base_units(Unit(channel.output_unit))
            else:
                raise TypeError(
                    f"Expected a digital or analog channel configuration, got "
                    f"{type(channel)}"
                )
            instructions[f"ch {channel_index}"] = InstructionCompilationParameters(
                description=channel.description,
                output=output,
                dtype=dtype,
                units=units,
            )

        stacked = compile_parallel_instructions(
            instructions,
            self.__configuration.time_step,
            shot_context,
        )

        return SequencerCompiler.SequencerShotParameters(sequence=stacked)

    def compute_trigger(
        self, sequencer_time_step: TimeStep, shot_context: ShotContext
    ) -> SequencerInstruction[np.bool_]:
        """Compile the trigger to generate for the current device."""

        length = number_time_steps(
            shot_context.get_shot_duration(), sequencer_time_step
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


@attrs.frozen
class InstructionCompilationParameters:
    """Specify how to evaluate an instruction for a channel.

    Attributes:
        description: A human-readable description of the channel.

            This is used to identify the channel in error messages.

        output: The output of the channel.

        dtype: The dtype in which the instruction will be converted once the output has
            been evaluated.

        units: The units in which the output of the channel is expressed.

            The units must be expressed in the base units.
            If the values are dimensionless, the units must be None.
    """

    description: str = attrs.field(converter=str)
    output: ChannelOutput = attrs.field(
        validator=attrs.validators.instance_of(ChannelOutput),
    )
    dtype: np.dtype = attrs.field(validator=attrs.validators.instance_of(np.dtype))
    units: Optional[Unit] = attrs.field(
        validator=attrs.validators.optional(attrs.validators.instance_of(Unit))
    )

    @units.validator  # type: ignore
    def _validate_units(self, _, units: Optional[Unit]):
        if units is not None:
            if not is_in_base_units(units):
                raise ValueError(
                    f"Unit {units} is not expressed in the base units of the registry."
                )
            if units.is_compatible_with(dimensionless):
                raise ValueError(f"Unit {units} is dimensionless and must be None.")


def compile_parallel_instructions(
    instructions: Mapping[str, InstructionCompilationParameters],
    time_step: TimeStep,
    shot_context: ShotContext,
) -> SequencerInstruction:
    """Evaluates and merges the output for different channels.

    Args:
        instructions: A mapping that indicates how to evaluate individual instructions.
        time_step: The time step used to evaluate the instructions.
        shot_context: The context of the shot.

    Returns:
        A :class:`SequencerInstruction` with multiple fields, each corresponding to the
        instruction passed in the `instructions` argument.
    """

    max_advance, max_delay = _find_max_advance_and_delays(
        [instruction.output for instruction in instructions.values()],
        time_step,
        shot_context.get_variables(),
    )

    channel_instructions = []
    exceptions = []
    for label, to_compile in instructions.items():
        try:
            output_series = to_compile.output.evaluate(
                time_step,
                max_advance,
                max_delay,
                shot_context,
            )
            instruction = _convert_series_to_instruction(output_series, to_compile)
            channel_instructions.append(with_name(instruction, label))
        except Exception as e:
            try:
                raise ChannelCompilationError(
                    f"Error occurred when evaluating output for "
                    f"'{to_compile.description}'"
                ) from e
            except ChannelCompilationError as channel_error:
                exceptions.append(channel_error)
    if exceptions:
        raise SequencerCompilationError(
            "Errors occurred when evaluating outputs",
            exceptions,
        )
    stacked = stack_instructions(*channel_instructions)
    return stacked


def _find_max_advance_and_delays(
    outputs: Iterable[ChannelOutput],
    time_step: TimeStep,
    variables: Mapping[DottedVariableName, Any],
) -> tuple[int, int]:
    advances_and_delays = [
        output.evaluate_max_advance_and_delay(time_step, variables)
        for output in outputs
    ]
    advances, delays = zip(*advances_and_delays)
    return max(advances), max(delays)


def get_master_clock_pulse(
    slave_time_step: TimeStep, master_time_step: TimeStep
) -> SequencerInstruction[np.bool_]:
    _, high, low = high_low_clicks(slave_time_step, master_time_step)
    single_clock_pulse = Pattern([True]) * high + Pattern([False]) * low
    assert len(single_clock_pulse) * master_time_step == slave_time_step
    return single_clock_pulse


def high_low_clicks(
    slave_time_step: TimeStep, master_timestep: TimeStep
) -> tuple[int, int, int]:
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
        raise InvalidValueError(
            "Slave time step must be at least twice the master sequencer time step"
        )
    div_decimal, mod = divmod(slave_time_step, master_timestep)
    if not mod == 0:
        raise InvalidValueError(
            "Slave time step must be an integer multiple of the master sequencer time "
            "step"
        )
    div, denominator = div_decimal.as_integer_ratio()
    assert denominator == 1
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


tblib.pickling_support.install(SequencerCompilationError, ChannelCompilationError)


def _convert_series_to_instruction(
    series: DimensionedSeries, instruction: InstructionCompilationParameters
) -> SequencerInstruction:
    if instruction.units != series.units:
        raise InvalidDimensionalityError(
            f"Instruction {instruction.description} output has units {series.units}, "
            f"expected {instruction.units}"
        )
    return series.values.as_type(instruction.dtype)
