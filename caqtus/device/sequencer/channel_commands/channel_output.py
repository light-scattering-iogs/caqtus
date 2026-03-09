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
from typing import Any

import attrs
import numpy as np

from caqtus.shot_compilation import ShotContext
from caqtus.shot_compilation.lane_compilation import DimensionedSeries
from caqtus.types.variable_name import DottedVariableName
from ..timing import TimeStep


@attrs.define
class ChannelOutput(abc.ABC):
    """Defines what should be outputted by a channel.

    Subclasses of this class should have specific attributes that define how to
    evaluate the series of values to output on the channel.

    These attributes can contain other :class:`ChannelOutput` instances, which allows
    to recursively combine transformations.
    """

    @abc.abstractmethod
    def evaluate[
        T: (np.number, np.bool_)
    ](
        self,
        required_time_step: TimeStep,
        prepend: int,
        append: int,
        shot_context: ShotContext,
    ) -> DimensionedSeries[T]:
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
        time_step: TimeStep,
        variables: Mapping[DottedVariableName, Any],
    ) -> tuple[int, int]:
        raise NotImplementedError
