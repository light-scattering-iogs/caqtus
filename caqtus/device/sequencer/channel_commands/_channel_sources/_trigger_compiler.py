from typing import Protocol, runtime_checkable

import numpy as np

from caqtus.shot_compilation import ShotContext, DeviceCompiler
from ...timming import TimeStep, number_time_steps
from ...instructions import SequencerInstruction, Pattern


@runtime_checkable
class TriggerableDeviceCompiler(DeviceCompiler, Protocol):
    """Defines the interface for a compiler that can compute the trigger of a device.

    The interface defined by this class is used when a sequencer is programmed to output
    the trigger for a device on one of its channels.
    To compute the trigger, the sequencer inspects the other device compiler and checks
    that it is a :class:`TriggerCompiler`.
    If that is the case, the sequencer calls the method :meth:`compute_trigger` of the
    other device compiler to know what to output.
    """

    def compute_trigger(
        self, sequencer_time_step: TimeStep, shot_context: ShotContext
    ) -> SequencerInstruction[np.bool_]:
        """Compute the trigger to be output for the associated device.

        The default implementation of this method provides a simple trigger that is
        high for the first half of the shot and low for the second half.

        Args:
            sequencer_time_step: The time step of the sequencer that need to output the
                trigger values, in ns.
            shot_context: Contains information about the shot being compiled.

        Returns:
            A boolean sequencer instruction containing the values that the trigger
            channel of the sequencer should take.
            The length of this instruction must be the number of ticks in the shot for
            the sequencer time step.
        """

        length = number_time_steps(
            shot_context.get_shot_duration(), sequencer_time_step
        )
        high_duration = length // 2
        low_duration = length - high_duration
        if high_duration == 0 or low_duration == 0:
            raise ValueError(
                "The shot duration is too short to generate a trigger pulse"
            )
        return Pattern([True]) * high_duration + Pattern([False]) * low_duration
