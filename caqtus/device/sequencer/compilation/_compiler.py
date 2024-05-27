from typing import Mapping, Any

import numpy as np

from caqtus.device import DeviceName, DeviceParameter
from caqtus.shot_compilation import DeviceCompiler, SequenceContext, ShotContext
from caqtus.types.units import Unit
from caqtus.types.variable_name import DottedVariableName
from ._evaluate_output import evaluate_output, _evaluate_expression_in_unit
from ..configuration import (
    SequencerConfiguration,
    ChannelConfiguration,
    DigitalChannelConfiguration,
    AnalogChannelConfiguration,
    ChannelOutput,
    is_value_source,
    TimeIndependentMapping,
    Advance,
    Delay,
)
from ..instructions import with_name, stack_instructions, SequencerInstruction


class SequencerCompiler(DeviceCompiler):

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
        max_advance, max_delay = self._find_max_advance_and_delays(
            shot_context.get_variables()
        )

        channel_instructions = []
        exceptions = []
        for channel_number, channel in enumerate(self.__configuration.channels):
            if isinstance(channel, AnalogChannelConfiguration):
                required_unit = Unit(channel.output_unit)
            else:
                required_unit = None
            try:
                output_values = evaluate_output(
                    channel.output,
                    self.__configuration.time_step,
                    required_unit,
                    max_advance,
                    max_delay,
                    shot_context,
                )
            except Exception as e:
                channel_error = ChannelCompilationError(
                    f"Error occurred when evaluating output for channel "
                    f"{channel_number} ({channel})"
                )
                channel_error.__cause__ = e
                exceptions.append(channel_error)
            else:
                instruction = _convert_channel_instruction(output_values, channel)
                channel_instructions.append(
                    with_name(instruction, f"ch {channel_number}")
                )
        if exceptions:
            raise SequencerCompilationError(
                f"Errors occurred when evaluating outputs for sequencer "
                f"{self.__device_name}",
                exceptions,
            )
        stacked = stack_instructions(channel_instructions)
        return {"sequence": stacked}

    def _find_max_advance_and_delays(
        self, variables: Mapping[DottedVariableName, Any]
    ) -> tuple[int, int]:
        advances_and_delays = [
            _evaluate_max_advance_and_delay(
                channel.output, self.__configuration.time_step, variables
            )
            for channel in self.__configuration.channels
        ]
        advances, delays = zip(*advances_and_delays)
        return max(advances), max(delays)


class SequencerCompilationError(ExceptionGroup):
    pass


class ChannelCompilationError(Exception):
    pass


def _evaluate_max_advance_and_delay(
    channel_function: ChannelOutput,
    time_step: int,
    variables: Mapping[DottedVariableName, Any],
) -> tuple[int, int]:
    if is_value_source(channel_function):
        return 0, 0
    elif isinstance(channel_function, TimeIndependentMapping):
        advances_and_delays = [
            _evaluate_max_advance_and_delay(input_, time_step, variables)
            for input_ in channel_function.inputs()
        ]
        advances, delays = zip(*advances_and_delays)
        return max(advances), max(delays)
    elif isinstance(channel_function, Advance):
        advance = _evaluate_expression_in_unit(
            channel_function.advance, Unit("ns"), variables
        )
        if advance < 0:
            raise ValueError(f"Advance must be a positive number.")
        advance_ticks = round(advance / time_step)
        input_advance, input_delay = _evaluate_max_advance_and_delay(
            channel_function.input_, time_step, variables
        )
        return advance_ticks + input_advance, input_delay
    elif isinstance(channel_function, Delay):
        delay = _evaluate_expression_in_unit(
            channel_function.delay, Unit("ns"), variables
        )
        if delay < 0:
            raise ValueError(f"Delay must be a positive number.")
        delay_ticks = round(delay / time_step)
        input_advance, input_delay = _evaluate_max_advance_and_delay(
            channel_function.input_, time_step, variables
        )
        return input_advance, delay_ticks + input_delay
    else:
        raise NotImplementedError(
            f"Cannot evaluate max advance and delay for {channel_function}"
        )


def _convert_channel_instruction(
    instruction: SequencerInstruction, channel: ChannelConfiguration
) -> SequencerInstruction:
    match channel:
        case DigitalChannelConfiguration():
            return instruction.as_type(np.dtype(np.bool_))
        case AnalogChannelConfiguration():
            return instruction.as_type(np.dtype(np.float64))
        case _:
            raise NotImplementedError
