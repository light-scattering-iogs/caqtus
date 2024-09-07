from abc import ABC, abstractmethod
from typing import Iterable

import attrs
import numpy as np

from .._image_type import Image, is_image
from .._shape import Width, Height


@attrs.define
class ROI(ABC):
    """Base class for regions of interest inside an image.

    Attributes:
        original_image_size: The size of the original image as (width, height).
    """

    original_image_size: tuple[Width, Height] = attrs.field(
        on_setattr=attrs.setters.validate,
    )

    @original_image_size.validator  # type: ignore
    def _validate_original_image_size(self, _, value):
        if not isinstance(value, tuple):
            raise TypeError(f"original_image_size must be a tuple, got {type(value)}")
        if len(value) != 2:
            raise ValueError(
                "original_image_size must be a tuple (width, height) with two elements"
            )
        if not all(isinstance(x, int) for x in value):
            raise ValueError("original_image_size must be a tuple of integers")
        if not all(x > 0 for x in value):
            raise ValueError("original_image_size must be a tuple of positive integers")

    def get_mask(self) -> np.ndarray:
        """A boolean array with the same shape as the original image.

        True values indicate that the pixel is part of the region of interest."""

        mask = np.full(self.original_image_size, False)
        mask[*self.get_indices()] = True
        return mask

    @abstractmethod
    def get_indices(self) -> tuple[Iterable[int], Iterable[int]]:
        """Return the indices of the pixels in the ROI."""

        raise NotImplementedError

    @property
    def original_width(self) -> int:
        """Return the width of the original image."""

        return self.original_image_size[0]

    @property
    def original_height(self) -> int:
        """Return the height of the original image."""

        return self.original_image_size[1]

    def apply[
        T: np.generic
    ](self, image: Image[T]) -> np.ma.MaskedArray[tuple[Width, Height], np.dtype[T]]:
        """Apply the ROI to an image.

        Returns:
            A masked array with the pixels outside the ROI masked.
        """

        if not is_image(image):
            raise TypeError(
                f"Image must be a numpy array with two dimensions, got {image}"
            )

        if image.shape != self.original_image_size:
            raise ValueError(
                f"Image shape {image.shape} does not match the roi original image size "
                f"{self.original_image_size}"
            )

        return np.ma.MaskedArray(image, mask=~self.get_mask())
