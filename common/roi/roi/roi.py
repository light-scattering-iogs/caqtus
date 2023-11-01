from abc import ABC, abstractmethod

import numpy as np

from image_types import Width, Height
from util import attrs


@attrs.define(slots=False)
class ROI(ABC):
    """Base class for regions of interest inside an image.

    Attributes:
        original_image_size: The size of the original image as (width, height)
    """

    original_image_size: tuple[Width, Height] = attrs.field(
        converter=tuple,
        on_setattr=attrs.setters.pipe(attrs.setters.convert, attrs.setters.validate),
    )

    @original_image_size.validator
    def _validate_original_image_size(self, _, value):
        if len(value) != 2:
            raise ValueError(
                "original_image_size must be a tuple (width, height) with two elements"
            )
        if not all(isinstance(x, int) for x in value):
            raise ValueError("original_image_size must be a tuple of integers")
        if not all(x > 0 for x in value):
            raise ValueError("original_image_size must be a tuple of positive integers")

    @abstractmethod
    def get_mask(self) -> np.ndarray:
        """A boolean array with the same shape as the original image.

        True values indicate that the pixel is part of the region of interest."""

        raise NotImplementedError()

    @property
    def original_width(self) -> int:
        """Return the width of the original image."""

        return self.original_image_size[0]

    @property
    def original_height(self) -> int:
        """Return the height of the original image."""

        return self.original_image_size[1]
