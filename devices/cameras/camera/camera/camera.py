from abc import ABC, abstractmethod
from collections import Counter
from math import inf

import numpy
from pydantic import Field, validator

from cdevice import CDevice


class CCamera(CDevice, ABC):
    external_trigger: bool = Field(
        description="Specify if the camera should wait for an external trigger to take a picture. "
        "If set to False, it will acquire images as fast as possible.",
        allow_mutation=False,
    )
    timeout: float = Field(
        default=inf,
        description="The camera must raise a TimeoutError if it is not able to acquire a picture withtin thei time.",
        allow_mutation=True,
    )
    picture_names: list[str] = Field(
        default_factory=list,
        description="Names to give to the pictures in order of acquisition. Each name must be unique.",
        allow_mutation=True,
    )
    exposures: list[float] = Field(
        default_factory=list,
        units="s",
        description="list of exposures to use for the pictures to acquire",
        allow_mutation=True,
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

    @abstractmethod
    def acquire_picture(self, exposure: float, timeout: float) -> [numpy.ndarray]:
        """Take a single picture

        Raises:
            TimeoutError if no picture was taken within timeout
        """

    def acquire_all_pictures(self) -> dict[str, numpy.ndarray]:
        """Take all the pictures specified by their names and exposures

        This function is blocking until all required pictures have been taken.
        Returns:
            pictures: a dictionary mapping picture name to a 2D numpy array
        """

        pictures = {}
        for name, exposure in zip(self.picture_names, self.exposures):
            pictures[name] = self.acquire_picture(exposure, self.timeout)

        return pictures
