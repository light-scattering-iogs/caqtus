import logging
from abc import ABC, abstractmethod
from collections import Counter
from math import inf
from typing import ClassVar

import numpy
from camera.configuration import ROI
from pydantic import Field, validator

from device import Device

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class CameraTimeoutError(TimeoutError):
    pass


class CCamera(Device, ABC):
    """Base class for a camera device

    Warnings:
        Classes inheriting of CCamera must implement _acquire_picture and subclass _read_picture.
    """

    picture_names: list[str] = Field(
        default_factory=list,
        description=(
            "Names to give to the pictures in order of acquisition. Each name must be"
            " unique."
        ),
        allow_mutation=False,
    )

    roi: ROI = Field(
        default_factory=ROI,
        allow_mutation=False,
        description="The region of interest to crop from a full image.",
    )
    timeout: float = Field(
        default=inf,
        units="s",
        description=(
            "The camera must raise a CameraTimeoutError if it is didn't receive a"
            " trigger within this time after starting acquisition."
        ),
        allow_mutation=True,
    )
    exposures: list[float] = Field(
        default_factory=list,
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

    def update_parameters(self, /, **kwargs) -> None:
        if "exposures" in kwargs:
            if self._acquired_pictures[0] and not self._acquired_pictures[-1]:
                raise RuntimeError(f"Not all pictures have been acquired")
        super().update_parameters(**kwargs)

    def acquire_picture(self):
        try:
            next_picture_index = self._acquired_pictures.index(False)
        except ValueError:
            next_picture_index = 0
            self._acquired_pictures = [False] * self.number_pictures_to_acquire
        logger.debug("Starting picture acquisition")
        self._acquire_picture(
            next_picture_index, self.exposures[next_picture_index], self.timeout
        )

    def acquire_all_pictures(self) -> None:
        """Take all the pictures specified by their names and exposures

        This function is blocking until all required pictures have been taken.
        """

        for _ in range(self.number_pictures_to_acquire):
            self.acquire_picture()

    def reset_acquisition(self):
        for i in range(len(self._acquired_pictures)):
            self._acquired_pictures[i] = False

    def read_picture(self, name: str) -> numpy.ndarray:
        picture_number = self.picture_names.index(name)
        return self._read_picture(picture_number)

    def read_all_pictures(self) -> dict[str, numpy.ndarray]:
        if not all(self._acquired_pictures):
            raise TimeoutError(
                f"Could not read all pictures on {self.name} "
                f"({sum(self._acquired_pictures)}/{self.number_pictures_to_acquire} acquired)"
            )
        else:
            return {name: self.read_picture(name) for name in self.picture_names}

    def shutdown(self):
        if not all(self._acquired_pictures):
            logger.warning(
                f"Only {sum(self._acquired_pictures)} out of"
                f" {self.number_pictures_to_acquire} pictures where successfully"
                f" acquired for {self.name}."
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

    def _has_exposure_changed(self, picture_number: int) -> bool:
        return picture_number == 0 or (
            self.exposures[picture_number - 1] != self.exposures[picture_number]
        )

    @abstractmethod
    def _acquire_picture(
        self, picture_number: int, exposure: float, timeout: float
    ) -> None:
        """Take a single picture

        When subclassing this function, it should start a single acquisition and be blocking until the picture is
        taken. After the acquisition, it should call the _pictured_acquired method.

        Raises:
            TimeoutError if no picture was taken within timeout
        """
        ...

    def _picture_acquired(self, picture_number: int):
        """Must be called when a picture has been taken"""
        self._acquired_pictures[picture_number] = True

    def _read_picture(self, picture_number: int) -> numpy.ndarray:
        """Read a previously acquired picture

        This method must be subclassed.
        """
        if not self._acquired_pictures[picture_number]:
            raise RuntimeError(f"Picture {picture_number} was not yet acquired")
        else:
            return numpy.array([[]])
