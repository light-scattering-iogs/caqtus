from typing import Mapping, Any

from caqtus.device import DeviceName, DeviceParameter
from caqtus.shot_compilation import (
    DeviceCompiler,
    SequenceContext,
    DeviceNotUsedException,
    ShotContext,
)
from caqtus.types.timelane import CameraTimeLane, TakePicture
from ._configuration import CameraConfiguration


class CameraCompiler(DeviceCompiler):
    """Compiler for a camera device."""

    def __init__(self, device_name: DeviceName, sequence_context: SequenceContext):
        super().__init__(device_name, sequence_context)
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
        for value, (start, stop) in zip(
            self.__lane.block_values(), self.__lane.bounds()
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
