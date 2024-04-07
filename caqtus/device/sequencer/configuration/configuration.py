from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import (
    Type,
    ClassVar,
    TypeVar,
    Generic,
    TypedDict,
    Any,
    TYPE_CHECKING,
)

import attrs
import numpy as np

from caqtus.device.configuration import DeviceConfiguration
from caqtus.device.name import DeviceName
from caqtus.types.units import Unit
from caqtus.types.variable_name import DottedVariableName
from ._evaluate_output import evaluate_output, _evaluate_expression_in_unit
from .channel_output import (
    ChannelOutput,
    is_channel_output,
    is_value_source,
    TimeIndependentMapping,
    Advance,
    Delay,
)
from .._controller import SequencerController
from ..instructions import SequencerInstruction, with_name, stack_instructions
from ..runtime import Sequencer
from ..trigger import Trigger, is_trigger

if TYPE_CHECKING:
    from caqtus.shot_compilation import (
        SequenceContext,
        ShotContext,
    )


def validate_channel_output(instance, attribute, value):
    if not is_channel_output(value):
        raise TypeError(f"Output {value} is not of type ChannelOutput")


@attrs.define
class ChannelConfiguration(ABC):
    """Contains information to computer the output of a channel."""

    description: str = attrs.field(
        converter=str,
        on_setattr=attrs.setters.convert,
    )
    output: ChannelOutput = attrs.field(
        validator=validate_channel_output,
        on_setattr=attrs.setters.validate,
    )


@attrs.define
class DigitalChannelConfiguration(ChannelConfiguration):
    def __str__(self):
        return f"digital channel '{self.description}'"


@attrs.define
class AnalogChannelConfiguration(ChannelConfiguration):
    output_unit: str = attrs.field(
        converter=str,
        on_setattr=attrs.setters.convert,
    )

    def __str__(self):
        return f"analog channel '{self.description}' with unit {self.output_unit}"


def validate_trigger(instance, attribute, value):
    if not is_trigger(value):
        raise TypeError(f"Trigger {value} is not of type Trigger")


SequencerType = TypeVar("SequencerType", bound=Sequencer)


class SequencerInitParams(TypedDict):
    time_step: int
    trigger: Trigger


class SequencerUpdateParams(TypedDict):
    sequence: SequencerInstruction


@attrs.define
class SequencerConfiguration(
    DeviceConfiguration[SequencerType], ABC, Generic[SequencerType]
):
    """Holds the static configuration of a sequencer device.

    Fields:
        number_channels: The number of channels of the device.
        time_step: The quantization time step used, in nanoseconds. The device can only
            update its output at multiples of this time step.
        channels: The configuration of the channels of the device. The length of this
            list must match the number of channels of the device.
    """

    number_channels: ClassVar[int]
    time_step: int = attrs.field(
        converter=int,
        validator=attrs.validators.ge(1),
        on_setattr=attrs.setters.pipe(attrs.setters.convert, attrs.setters.validate),
    )
    channels: tuple[ChannelConfiguration, ...] = attrs.field(
        converter=tuple,
        validator=attrs.validators.deep_iterable(
            member_validator=attrs.validators.instance_of(ChannelConfiguration)
        ),
        on_setattr=attrs.setters.pipe(attrs.setters.convert, attrs.setters.validate),
    )
    trigger: Trigger = attrs.field(validator=validate_trigger)

    @classmethod
    @abstractmethod
    def channel_types(cls) -> tuple[Type[ChannelConfiguration], ...]: ...

    @channels.validator  # type: ignore
    def validate_channels(self, _, channels):
        if len(channels) != self.number_channels:
            raise ValueError(
                f"The length of channels ({len(channels)}) doesn't match the number of"
                f" channels {self.number_channels}"
            )
        for channel, channel_type in zip(channels, self.channel_types(), strict=True):
            if not isinstance(channel, channel_type):
                raise TypeError(
                    f"Channel {channel} is not of the expected type {channel_type}"
                )

    def __getitem__(self, item):
        return self.channels[item]

    @abstractmethod
    def get_device_initialization_method(
        self, device_name: DeviceName, sequence_context: "SequenceContext"
    ):
        # TODO: raise DeviceNotUsedException if the sequencer is not used for the
        #  current sequence
        initialization_method = super().get_device_initialization_method(
            device_name, sequence_context
        )
        initialization_method.init_kwargs.update(
            {"time_step": self.time_step, "trigger": self.trigger}
        )
        return initialization_method

    def get_controller_type(self):
        return SequencerController

    @abstractmethod
    def compile_device_shot_parameters(
        self,
        device_name: DeviceName,
        shot_context: "ShotContext",
    ) -> SequencerUpdateParams:
        max_advance, max_delay = self._find_max_advance_and_delays(
            shot_context.get_variables()
        )

        channel_instructions = []
        exceptions = []
        for channel_number, channel in enumerate(self.channels):
            if isinstance(channel, AnalogChannelConfiguration):
                required_unit = Unit(channel.output_unit)
            else:
                required_unit = None
            try:
                output_values = evaluate_output(
                    channel.output,
                    self.time_step,
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
                f"Errors occurred when evaluating outputs for sequencer {device_name}",
                exceptions,
            )
        stacked = stack_instructions(channel_instructions)
        return {"sequence": stacked}

    def _find_max_advance_and_delays(
        self, variables: Mapping[DottedVariableName, Any]
    ) -> tuple[int, int]:
        advances_and_delays = [
            _evaluate_max_advance_and_delay(channel.output, self.time_step, variables)
            for channel in self.channels
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
