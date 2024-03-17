import abc
import contextlib
import logging
from collections.abc import Iterable
from typing import ClassVar

from attrs import define, field
from attrs.setters import frozen, convert
from attrs.validators import instance_of
from core.device import Device
from core.types.image import Image

from .configuration import RectangularROI

logger = logging.getLogger(__name__)


class CameraTimeoutError(TimeoutError):
    pass


@define(slots=False)
class Camera(Device, abc.ABC):
    """Define the interface for a camera.

    This is an abstract class that must be subclassed to implement a specific camera.
    When using a device inheriting from this class , it is required to know the
    number of pictures that will be acquired before starting an acquisition.
    Devices of this class are not meant to be used in video mode.
    """

    sensor_width: ClassVar[int]
    sensor_height: ClassVar[int]

    roi: RectangularROI = field(
        validator=instance_of(RectangularROI), on_setattr=frozen
    )
    timeout: float = field(converter=float, on_setattr=convert)
    external_trigger: bool = field(validator=instance_of(bool), on_setattr=frozen)

    @roi.validator  # type: ignore
    def _validate_roi(self, _, value: RectangularROI):
        if value.original_image_size != (self.sensor_width, self.sensor_height):
            raise ValueError(
                f"The original image size of the ROI {value.original_image_size} "
                f"does not match the sensor size "
                f"{self.sensor_width}x{self.sensor_height}"
            )

    @abc.abstractmethod
    def update_parameters(self, timeout: float) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def acquire(
        self, exposures: list[float]
    ) -> contextlib.AbstractContextManager[Iterable[Image]]:
        """Acquire images with the given exposure times.

        The result is a context manager that returns an iterable of images.
        Each image in the iterable is acquired with the corresponding exposure time.

        This demonstrates how to use the context manager returned by this method:

        .. code-block:: python

                with camera.acquire(exposures=[0.1, 0.5, 1.0]) as images:
                    for image in images:
                        print(image)

        There are two possible behaviors when implementing this method for a given
        camera:
        - The camera can gather all images and return them all in the end.
        - The camera can yield images as they become available. This make it possible
            to process images as they are acquired.

        Raises:
            CameraTimeoutError: If external trigger is enabled and the camera does not
                receive a trigger signal within the timeout.
        """

        raise NotImplementedError

    def take_picture(self, exposure: float) -> Image:
        """Acquire a single image with the given exposure time."""

        with self.acquire([exposure]) as images:
            return next(iter(images))
