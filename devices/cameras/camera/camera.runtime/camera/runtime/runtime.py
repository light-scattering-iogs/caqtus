import logging
import time
from abc import ABC, abstractmethod
from collections import Counter
from typing import ClassVar, Optional

import numpy
from pydantic import Field, validator

from camera.configuration import ROI
from device import RuntimeDevice

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class CameraTimeoutError(TimeoutError):
    pass


class CCamera(RuntimeDevice, ABC):
    """Define the interface for a camera.

    This is an abstract class that must be subclassed to implement a specific camera.
    When using a device inheriting from this class , it is required to know the number
    of pictures that will be acquired before starting an acquisitions. Devices of this
    class are not meant to be used in video mode.

    Attributes:
        picture_names: Names to give to the pictures in order of acquisition. Each name
            must be unique. This will define the number of picture to take during one
            acquisition, and it is frozen after initialization.
        roi: The region of interest to keep from the full sensor image. Depending on the
            device, this can be enforced before or after retrieving the image from the
            camera.
        timeout: The camera must raise a CameraTimeoutError if it didn't receive a
            trigger within this time after starting acquisition.
            The timeout is in seconds.
        exposures: List of exposures to use for the pictures to acquire. The length of
            the list must match the length of picture_names.
            Each exposure is in seconds.
        external_trigger: Specify if the camera should wait for an external trigger to
            take a picture. If set to False, it should acquire images as fast as
            possible.

    Classes inheriting of CCamera must implement the following methods:
    - _start_acquisition
    - _stop_acquisition
    - _is_acquisition_in_progress
    """

    picture_names: tuple[str, ...] = Field(allow_mutation=False)
    roi: ROI = Field(allow_mutation=False)
    timeout: float = Field(units="s", allow_mutation=True)
    exposures: list[float] = Field(units="s", allow_mutation=True)
    external_trigger: bool = Field(allow_mutation=False)

    sensor_width: ClassVar[int]
    sensor_height: ClassVar[int]

    _pictures: list[Optional[numpy.ndarray]] = []

    @validator("picture_names")
    def validate_picture_names(cls, picture_names):
        names = list(picture_names)
        counts = Counter(names)
        for name, count in counts.items():
            if count > 1:
                raise ValueError(f"Picture name {name} is used several times")
        return names

    @validator("exposures")
    def validate_exposures(cls, exposures, values):
        num_exposures = len(exposures)
        num_names = len(values["picture_names"])
        if num_names != num_exposures:
            raise ValueError(
                f"Number of picture names ({num_names}) and of exposures"
                f" ({num_exposures}) must match"
            )

        if any(exposure > values["timeout"] for exposure in exposures):
            raise ValueError(f"Exposure is longer than timeout")
        return exposures

    def start(self):
        super().start()

    def update_parameters(self, exposures: list[float], timeout: float) -> None:
        """Update the exposures time of the camera"""

        if not (self.are_all_pictures_acquired() or self.no_pictures_acquired()):
            raise RuntimeError(
                f"Cannot update parameters while pictures are being acquired"
            )

        super().update_parameters(exposures=exposures, timeout=timeout)

    def are_all_pictures_acquired(self):
        return all(picture is not None for picture in self._pictures)

    def no_pictures_acquired(self):
        return all(picture is None for picture in self._pictures)

    def start_acquisition(self):
        self._pictures = [None] * self.number_pictures_to_acquire
        self._start_acquisition(self.number_pictures_to_acquire)

    def is_acquisition_in_progress(self) -> bool:
        return self._is_acquisition_in_progress()

    def stop_acquisition(self):
        self._stop_acquisition()

    @abstractmethod
    def _start_acquisition(self, number_pictures: int):
        """Start the acquisition of pictures

        To implement in subclasses.

        Actual camera implementation must implement this method. It must start the acquisition of pictures and return as
        soon as possible. It should raise an error if the acquisition could not be started or is already in progress.
        The acquisition must be stopped by calling _stop_acquisition.

        Args:
            number_pictures: Number of pictures to acquire.

        Raises:
            CameraTimeoutError: If the camera didn't receive a trigger within the timeout after starting acquisition.
            If this error is raised, the acquisition will be stopped, but it informs the experiment manager that it can
            retry this acquisition.
        """
        ...

    @abstractmethod
    def _is_acquisition_in_progress(self) -> bool:
        """Return True if the acquisition is in progress, False otherwise

        To implement in subclasses.
        """
        ...

    @abstractmethod
    def _stop_acquisition(self):
        """Stop the acquisition of pictures

        To implement in subclasses.
        """
        ...

    def acquire_all_pictures(self) -> None:
        """Take all the pictures specified by their names and exposures

        This function is blocking until all required pictures have been taken.
        """

        self.start_acquisition()
        while self.is_acquisition_in_progress():
            time.sleep(10e-3)
        self.stop_acquisition()

    def read_all_pictures(self) -> dict[str, numpy.ndarray]:
        if not self.are_all_pictures_acquired():
            raise CameraTimeoutError(
                f"Not all pictures have been acquired for camera {self.name}"
            )
        else:
            return {
                name: self._pictures[index]
                for index, name in enumerate(self.picture_names)
            }

    def shutdown(self):
        try:
            if self.is_acquisition_in_progress():
                self.stop_acquisition()
            if not (self.are_all_pictures_acquired() or self.no_pictures_acquired()):
                logger.warning(
                    f"Shutting down {self.name} while acquisition is in progress"
                )
        finally:
            super().shutdown()

    @classmethod
    def exposed_remote_methods(cls) -> tuple[str, ...]:
        return super().exposed_remote_methods() + (
            "acquire_picture",
            "acquire_all_pictures",
            "read_picture",
            "read_all_pictures",
            "reset_acquisition",
        )

    @property
    def number_pictures_to_acquire(self):
        return len(self.picture_names)
