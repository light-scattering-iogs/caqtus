"""This module defines the configuration used to compute the output of a sequencer
channel.

A channel can typically output a constant value, the values of a lane, a trigger for
another device, or a functional combination of these.

The union type `ChannelOutput` is used to represent the different possible outputs of a
channel.
Each possible type of output is represented by a different class.
An output class is a high-level description of what should be outputted by a channel.
The classes defined are only declarative and do not contain any logic to compute the
output.
For more information on how the output is evaluated, see
:mod:`core.compilation.sequencer_parameter_compiler`.
"""

from __future__ import annotations

import abc
from collections.abc import Mapping
from typing import Optional, Any

import attrs
import numpy as np

from caqtus.device.sequencer.instructions import SequencerInstruction
from caqtus.shot_compilation import ShotContext
from caqtus.types.units import Unit, dimensionless
from caqtus.types.variable_name import DottedVariableName


@attrs.frozen
class EvaluatedOutput[T: np.number]:
    """Represents a series of value to output on a channel.

    Parameters:
        values: The sequence of values to output.
        units: The units in which the values are expressed.
            The units must be expressed in the base units of the registry.
            If the values are dimensionless, the units must be `None`.
    """

    values: SequencerInstruction[T]
    units: Optional[Unit] = attrs.field(
        validator=attrs.validators.optional(attrs.validators.instance_of(Unit))
    )

    @units.validator
    def _validate_units(self, _, units: Optional[Unit]):
        if units is not None:
            base_units = (1 * units).to_base_units().units
            if base_units != units:
                raise ValueError(
                    f"Unit {units} is not expressed in the base units of the registry."
                )
            if units.is_compatible_with(dimensionless):
                raise ValueError(f"Unit {units} is dimensionless and must be None.")


@attrs.define
class ChannelOutput(abc.ABC):
    @abc.abstractmethod
    def evaluate(
        self,
        required_time_step: int,
        prepend: int,
        append: int,
        shot_context: ShotContext,
    ) -> EvaluatedOutput:
        """Evaluate the output of a channel with the required parameters.

        Args:
            required_time_step: The time step in which to evaluate the output, in ns.
            prepend: The number of time steps to add at the beginning of the output.
            append: The number of time steps to add at the end of the output.
            shot_context: Contains information about the current to evaluate the output.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def evaluate_max_advance_and_delay(
        self,
        time_step: int,
        variables: Mapping[DottedVariableName, Any],
    ) -> tuple[int, int]:
        raise NotImplementedError
