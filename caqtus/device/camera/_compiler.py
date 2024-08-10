from typing import Mapping, Any, assert_never

import numpy as np

from caqtus.device import DeviceName, DeviceParameter
from caqtus.shot_compilation import (
    SequenceContext,
    DeviceNotUsedException,
    ShotContext,
)
from caqtus.shot_compilation.lane_compilers.timing import number_ticks, ns
from caqtus.types.recoverable_exceptions import InvalidValueError
from caqtus.types.timelane import CameraTimeLane, TakePicture
from ._configuration import CameraConfiguration
from ..sequencer.compilation import TriggerableDeviceCompiler
from ..sequencer.instructions import SequencerInstruction, Pattern, concatenate


class CameraCompiler(TriggerableDeviceCompiler):
    """Compiler for a camera device."""

    def __init__(self, device_name: DeviceName, sequence_context: SequenceContext):
        super().__init__(device_name, sequence_context)
        self.__device_name = device_name
        try:
            lane = sequence_context.get_lane(device_name)
        except KeyError:
            raise DeviceNotUsedException(device_name)
        if not isinstance(lane, CameraTimeLane):
            raise TypeError(
                f"Expected a camera time lane for device {device_name}, got "
                f"{type(lane)}"
            )
        self.__lane = lane
        configuration = sequence_context.get_device_configuration(device_name)
        if not isinstance(configuration, CameraConfiguration):
            raise TypeError(
                f"Expected a camera configuration for device {device_name}, got "
                f"{type(configuration)}"
            )
        self.__configuration = configuration

    def compile_initialization_parameters(self) -> Mapping[DeviceParameter, Any]:
        return {
            DeviceParameter("roi"): self.__configuration.roi,
            DeviceParameter("external_trigger"): True,
            DeviceParameter("timeout"): 1.0,
        }

    def compile_shot_parameters(self, shot_context: ShotContext) -> Mapping[str, Any]:
        step_durations = shot_context.get_step_durations()
        exposures = []
        picture_names = []
        shot_context.mark_lane_used(self.__device_name)
        for value, (start, stop) in zip(
            self.__lane.block_values(), self.__lane.block_bounds()
        ):
            if isinstance(value, TakePicture):
                exposure = sum(step_durations[start:stop])
                exposures.append(exposure)
                picture_names.append(value.picture_name)
        return {
            # Add a bit of extra time to the timeout, in case the shot takes a bit of
            # time to actually start.
            "timeout": shot_context.get_shot_duration() + 1,
            "picture_names": picture_names,
            "exposures": exposures,
        }

    def compute_trigger(
        self, sequencer_time_step: int, shot_context: ShotContext
    ) -> SequencerInstruction[np.bool_]:
        step_bounds = shot_context.get_step_start_times()

        instructions: list[SequencerInstruction[np.bool_]] = []
        for value, (start, stop) in zip(
            self.__lane.block_values(), self.__lane.block_bounds()
        ):
            length = number_ticks(
                step_bounds[start], step_bounds[stop], sequencer_time_step * ns
            )
            if isinstance(value, TakePicture):
                if length == 0:
                    raise InvalidValueError(
                        f"No trigger can be generated for picture "
                        f"'{value.picture_name}' because its exposure is too short"
                        f"({(step_bounds[stop] - step_bounds[start]) * 1e9} ns) with "
                        f"respect to the time step ({sequencer_time_step} ns)"
                    )
                instructions.append(Pattern([True]) * length)
            elif value is None:
                instructions.append(Pattern([False]) * length)
            else:
                assert_never(value)
        return concatenate(*instructions)
