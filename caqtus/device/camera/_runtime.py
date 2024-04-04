import abc
import contextlib
import logging
from collections.abc import Iterable, Generator
from typing import ClassVar, ParamSpec, Generic

from attrs import define, field
from attrs.setters import frozen, convert
from attrs.validators import instance_of

from caqtus.device import Device
from caqtus.types.image import Image
from ._configuration import RectangularROI

logger = logging.getLogger(__name__)


class CameraTimeoutError(TimeoutError):
    pass


P = ParamSpec("P")


@define(slots=False)
class Camera(Device, abc.ABC, Generic[P]):
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
    def update_parameters(
        self, timeout: float, *args: P.args, **kwargs: P.kwargs
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def _start_acquisition(self, exposures: list[float]) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def _read_image(self, exposure: float) -> Image:
        raise NotImplementedError

    @abc.abstractmethod
    def _stop_acquisition(self) -> None:
        raise NotImplementedError

    @contextlib.contextmanager
    def acquire(self, exposures: list[float]) -> Generator[Iterable[Image], None, None]:
        """Acquire images with the given exposure times.

        The result is a context manager that returns an iterable of images.
        Each image in the iterable is acquired with the corresponding exposure time.

        This demonstrates how to use the context manager returned by this method:

        .. code-block:: python

                with camera.acquire(exposures=[0.1, 0.5, 1.0]) as images:
                    for image in images:
                        print(image)

        Raises:
            CameraTimeoutError: If external trigger is enabled and the camera does not
                receive a trigger signal within the timeout.
        """

        self._start_acquisition(exposures)
        try:
            yield self._acquire_pictures(exposures)
        finally:
            self._stop_acquisition()

    def _acquire_pictures(self, exposures: list[float]) -> Iterable[Image]:
        for exposure in exposures:
            yield self._read_image(exposure)

    def take_picture(self, exposure: float) -> Image:
        """Acquire a single image with the given exposure time."""

        with self.acquire([exposure]) as images:
            return next(iter(images))
