from typing import Mapping, Any

import numpy as np

import caqtus.formatter as fmt
from caqtus.device import DeviceName, DeviceParameter
from caqtus.shot_compilation import DeviceCompiler, SequenceContext, ShotContext
from caqtus.types.units import Unit, InvalidDimensionalityError, dimensionless
from caqtus.types.units.base import base_units
from caqtus.types.variable_name import DottedVariableName
from ..channel_commands import DimensionedSeries
from ..configuration import (
    SequencerConfiguration,
    ChannelConfiguration,
    DigitalChannelConfiguration,
    AnalogChannelConfiguration,
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
