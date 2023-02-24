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
    """Base class for a camera device

    Warnings:
        Classes inheriting of CCamera must implement _acquire_picture and subclass _read_picture.
    """

    picture_names: tuple[str] = Field(
        description=(
            "Names to give to the pictures in order of acquisition. Each name must be"
            " unique."
        ),
        allow_mutation=False,
    )

    roi: ROI = Field(
        allow_mutation=False,
        description="The region of interest to crop from a full image.",
    )
    timeout: float = Field(
        units="s",
        description=(
            "The camera must raise a CameraTimeoutError if it is didn't receive a"
            " trigger within this time after starting acquisition."
        ),
        allow_mutation=True,
    )
    exposures: list[float] = Field(
        units="s",
        description="List of exposures to use for the pictures to acquire.",
        allow_mutation=True,
    )
    external_trigger: bool = Field(
        description=(
            "Specify if the camera should wait for an external trigger to take a"
            " picture. If set to False, it will acquire images as fast as possible."
        ),
        allow_mutation=False,
    )

    sensor_width: ClassVar[int]
    sensor_height: ClassVar[int]

    _acquired_pictures: list[bool] = []
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
        self._acquired_pictures = [False] * self.number_pictures_to_acquire

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
        self._start_acquisition()

    def is_acquisition_in_progress(self) -> bool:
        return self._is_acquisition_in_progress()

    def stop_acquisition(self):
        self._stop_acquisition()

    @abstractmethod
    def _start_acquisition(self):
        """Start the acquisition of pictures

        Warnings:
            This function must not block until all pictures have been acquired, but it must return as soon as the camera
            starts waiting for images.
        """
        ...

    @abstractmethod
    def _is_acquisition_in_progress(self) -> bool:
        """Return True if the acquisition is in progress"""
        ...

    @abstractmethod
    def _stop_acquisition(self):
        """Stop the acquisition of pictures"""
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
            raise TimeoutError(
                f"Not all pictures have been acquired for camera {self.name}"
            )
        else:
            return {
                name: self._pictures[index]
                for index, name in enumerate(self.picture_names)
            }

    def shutdown(self):
        if self.is_acquisition_in_progress():
            self.stop_acquisition()
        if not (self.are_all_pictures_acquired() or self.no_pictures_acquired()):
            logger.warning(
                f"Shutting down {self.name} while acquisition is in progress"
            )
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
