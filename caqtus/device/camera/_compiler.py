from typing import assert_never, TypedDict

import numpy as np

from caqtus.device import DeviceName
from caqtus.shot_compilation import (
    SequenceContext,
    DeviceNotUsedException,
    ShotContext,
)
from caqtus.shot_compilation.timed_instructions import (
    SequencerInstruction,
    Pattern,
    concatenate,
)
from caqtus.types.recoverable_exceptions import InvalidValueError
from caqtus.types.timelane import CameraTimeLane, TakePicture
from ._configuration import CameraConfiguration
from ..sequencer import TimeStep
from ..sequencer.compilation import TriggerableDeviceCompiler
from ..sequencer.timing import ns, number_time_steps_between
from ...types.image.roi import RectangularROI


class CameraCompiler(TriggerableDeviceCompiler):
    """Computes parameters for a camera device."""

    def __init__(self, device_name: DeviceName, sequence_context: SequenceContext):
        super().__init__(device_name, sequence_context)
        self.__device_name = device_name
        try:
            lane = sequence_context.get_lane(device_name)
        except KeyError:
            raise DeviceNotUsedException(device_name) from None
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

    class CameraInitializationParameters(TypedDict):
        """The parameters to pass to the camera constructor.

        This dictionary contains the following keys:

            * roi: The region of interest of the sensor for the camera during the
                sequence.
            * external_trigger: Whether the camera should be triggered externally or
                not.
            * timeout: The maximum time to wait for the camera to be ready to take a
                picture.
        """

        roi: RectangularROI
        external_trigger: bool
        timeout: float

    def compile_initialization_parameters(self) -> CameraInitializationParameters:
        """Compile the parameters to pass to the device constructor."""

        return self.CameraInitializationParameters(
            roi=self.__configuration.roi,
            external_trigger=True,
            timeout=1.0,
        )

    class CameraShotParameters(TypedDict):
        """The parameters to pass to the camera controller for a shot.

        This dictionary contains the following keys:

            * timeout: The maximum time to wait for a picture to be taken.
            * picture_names: The names of the pictures to take, in the order they
                should be taken.
            * exposures: The exposure times of the pictures to take, in the order they
                should be taken.
                The number of exposures matches the number of pictures.
        """

        timeout: float
        picture_names: list[str]
        exposures: list[float]

    def compile_shot_parameters(
        self, shot_context: ShotContext
    ) -> CameraShotParameters:
        """Compile the parameters to pass to the camera controller for a shot.

        The exposures for the pictures are computed from the duration of the
        corresponding blocks in the camera time lane.
        """

        step_durations = shot_context.get_step_durations()
        exposures: list[float] = []
        picture_names = []
        shot_context.mark_lane_used(self.__device_name)
        for value, (start, stop) in zip(
            self.__lane.block_values(), self.__lane.block_bounds(), strict=True
        ):
            if isinstance(value, TakePicture):
                exposure = sum(step_durations[start:stop])
                exposures.append(float(exposure))
                picture_names.append(value.picture_name)
        return self.CameraShotParameters(
            # Add a bit of extra time to the timeout, in case the shot takes a bit of
            # time to actually start.
            timeout=float(shot_context.get_shot_duration() + 1),
            picture_names=picture_names,
            exposures=exposures,
        )

    def compute_trigger(
        self, sequencer_time_step: TimeStep, shot_context: ShotContext
    ) -> SequencerInstruction[np.bool_]:
        """Compute the trigger for the camera.

        For a camera, the trigger is high during the exposure time of each picture,
        and low in between.
        """

        step_bounds = shot_context.get_step_start_times()

        instructions: list[SequencerInstruction[np.bool_]] = []
        for value, (start, stop) in zip(
            self.__lane.block_values(), self.__lane.block_bounds(), strict=True
        ):
            length = number_time_steps_between(
                step_bounds[start], step_bounds[stop], sequencer_time_step
            )
            if isinstance(value, TakePicture):
                if length == 0:
                    raise InvalidValueError(
                        f"No trigger can be generated for picture "
                        f"'{value.picture_name}' because its exposure is too short"
                        f"({(step_bounds[stop] - step_bounds[start]) / ns} ns) with "
                        f"respect to the time step ({sequencer_time_step} ns)"
                    )
                instructions.append(Pattern([True]) * length)
            elif value is None:
                instructions.append(Pattern([False]) * length)
            else:
                assert_never(value)
        return concatenate(*instructions)
