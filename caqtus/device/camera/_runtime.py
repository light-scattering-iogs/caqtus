import abc
from collections.abc import Iterator
from contextlib import AbstractContextManager
from typing import ClassVar

from attrs import define, field
from attrs.setters import frozen, convert
from attrs.validators import instance_of

from caqtus.device import Device
from caqtus.types.image import Image
from ._configuration import RectangularROI


class CameraTimeoutError(TimeoutError):
    """Raised when the camera did not acquire an image after a given timeout."""

    pass


@define(slots=False)
class Camera(Device, abc.ABC):
    """Define the interface for a camera instrument.

    This is an abstract class that must be subclassed to implement a specific camera.
    Subclasses must implement the :meth:`update_parameters` and :meth:`acquire` methods.

    Attributes:
        roi: A rectangular subset of the sensor that defines the region of interest.
            Images returned by the camera must be of the same size as the region of
            interest.
            Some camera models allow to define the region of interest before even
            fetching the image from the instrument.
            This is the recommended way to crop the region of interest, as it will
            reduce the amount of data transferred from the camera to the computer.
            If the camera does not support defining the region of interest before
            fetching the image, the region of interest should be cropped after the image
            is acquired and before it is returned to the user.
            This attribute can only be set with the :method:`__init__` method.
        timeout: The maximum time in seconds that the camera must wait for an external
            trigger signal before raising a :class:`CameraTimeoutError`.
        external_trigger: A boolean that indicates if the camera is waiting for an
            external trigger signal to acquire an image.
            If this is set to True, the camera will wait for the trigger signal before
            acquiring an image.
            If this is set to False, the camera will acquire an image as soon as
            possible after the acquisition is started.
            This attribute can only be set with the :method:`__init__` method.
        sensor_width: A class attribute that defines the width of the sensor in pixels.
            This attribute must be set in the subclass implementation.
        sensor_height: A class attribute that defines the height of the sensor in
            pixels.
            This attribute must be set in the subclass implementation.
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
    def update_parameters(self, timeout: float, *args, **kwargs) -> None:
        """Update the camera parameters between acquisitions.

        It is undefined what should happen if this method is called while the camera is
        acquiring images.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def acquire(
        self, exposures: list[float]
    ) -> AbstractContextManager[Iterator[Image]]:
        """Acquire images with the given exposure times.

        Returns:
            A context manager that yields an iterator of images.
            When the context manager is entered, the camera starts the acquisition of
            the number of images specified by the length of the exposures list.

            Iterating over the iterator returned by the context manager will yield the
            images as they are acquired by the camera.
            It is recommended to yield the images as they are acquired, and not to wait
            for all the images to be acquired before returning them.
            This allows to do some processing on the images and to react to them while
            the camera is still acquiring the next ones.

            When the context manager exits, the camera stops the acquisition.

        Example:
              This demonstrates how to use this method to take images:

              .. code-block:: python

                with camera.acquire(exposures=[0.1, 0.5, 1.0]) as images:
                    for image in images:
                        print(image)

        Raises:
            The iterator raises a :class:`CameraTimeoutError` if the camera does not
            acquire an image after the timeout specified by the method
            :meth:`update_parameters`.
            The context manager should raise an error if it is exited without error
            before the acquisition is completed.
        """

        raise NotImplementedError

    def take_picture(self, exposure: float) -> Image:
        """A convenience method to acquire a single image."""

        with self.acquire([exposure]) as images:
            return next(iter(images))
