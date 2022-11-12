from abc import ABC, abstractmethod
from collections import Counter
from math import inf

import numpy
import pydantic
from cdevice import CDevice
from pydantic import Field, validator
from typing_extensions import ClassVar


class ROI(pydantic.BaseModel):
    x: int = Field(
        description="horizontal coordinate of the corner of the roi",
    )
    width: int = Field(description="width of the roi")
    y: int = Field(description="x coordinate of the corner of the roi")
    height: int = Field(description="height of the roi")


class CCamera(CDevice, ABC):
    """Base class for a camera device

    Warnings:
        Classes inheriting of CCamera must implement _acquire_picture and subclass _read_picture.
    """

    picture_names: list[str] = Field(
        default_factory=list,
        description="Names to give to the pictures in order of acquisition. Each name must be unique.",
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
        description="The camera must raise a TimeoutError if it is not able to acquire a picture within this time.",
        allow_mutation=True,
    )
    exposures: list[float] = Field(
        default_factory=list,
        units="s",
        description="List of exposures to use for the pictures to acquire.",
        allow_mutation=True,
    )
    external_trigger: bool = Field(
        description="Specify if the camera should wait for an external trigger to take a picture. "
        "If set to False, it will acquire images as fast as possible.",
        allow_mutation=False,
    )

    sensor_width: ClassVar[int]
    sensor_height: ClassVar[int]

    _acquired_pictures: list[bool] = []

    @classmethod
    def exposed_remote_methods(cls) -> tuple[str, ...]:
        return super().exposed_remote_methods() + (
            "acquire_picture",
            "acquire_all_pictures",
            "read_picture",
        )

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
                f"Number of picture names ({num_names}) and of exposures ({num_exposures}) must match"
            )

        if any(exposure > values["timeout"] for exposure in exposures):
            raise ValueError(f"Exposure is longer than timeout")
        return exposures

    @property
    def number_pictures_to_acquire(self):
        return len(self.picture_names)

    def start(self):
        super().start()
        self._acquired_pictures = [False] * self.number_pictures_to_acquire

    def shutdown(self):
        if not all(self._acquired_pictures):
            raise UserWarning(
                f"Only {sum(self._acquired_pictures)} out of {self.number_pictures_to_acquire} pictures where "
                f"successfully acquired for {self.name}"
            )
        super().shutdown()

    def apply_rt_variables(self, /, **kwargs) -> None:
        if "exposures" in kwargs:
            if not all(self._acquired_pictures):
                raise RuntimeError(f"Not all pictures have been acquired")
        super().apply_rt_variables(**kwargs)

    def acquire_picture(self):
        try:
            next_picture_index = self._acquired_pictures.index(False)
        except ValueError:
            next_picture_index = 0
            self._acquired_pictures = [False] * self.number_pictures_to_acquire
        self._acquire_picture(
            next_picture_index, self.exposures[next_picture_index], self.timeout
        )

    def acquire_all_pictures(self) -> dict[str, numpy.ndarray]:
        """Take all the pictures specified by their names and exposures

        This function is blocking until all required pictures have been taken.
        Returns:
            pictures: a dictionary mapping picture name to a 2D numpy array
        """

        pictures = {}
        for name, exposure in zip(self.picture_names, self.exposures):
            self.acquire_picture()
            pictures[name] = self.read_picture(name)

        return pictures

    def read_picture(self, name: str) -> numpy.ndarray:
        picture_number = self.picture_names.index(name)
        return self._read_picture(picture_number)

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
