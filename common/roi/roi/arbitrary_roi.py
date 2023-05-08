from typing import Self

import numpy as np
from pydantic import validator

from .roi import BaseROI


class ArbitraryROI(BaseROI):
    """Arbitrary region of interest inside an image.

    This ROI is defined by specifying the indices of the pixels in the original image that are part of the region of
    interest.

    While this ROI is the most generic one, it becomes very inefficient when the number of pixels in the region of
    interest is large, because it stores the coordinates of all pixels. Whenever possible, use a more specific ROI.

    Attributes:
        indices: The indices of the pixels in the original image that are part of the region of interest.
    """

    indices: tuple[tuple[int, int], ...]

    @property
    def mask(self) -> np.ndarray:
        """A boolean array with the same shape as the original image.

        True values indicate that the pixel is part of the region of interest."""

        mask = np.full(self.original_image_size, False)
        mask[*np.array(self.indices).T] = True
        return mask

    @classmethod
    def from_mask(cls, mask: np.ndarray) -> Self:
        """Create a region of interest from a mask

        Args:
            mask: A boolean array with the same shape as the original image. True values indicate that the pixel is part
            of the region of interest.
        """

        shape = mask.shape
        if len(shape) != 2:
            raise ValueError("mask must be 2D")
        shape = shape[0], shape[1]
        return cls(original_image_size=shape, indices=np.argwhere(mask).tolist())

    @validator("indices")
    def validate_indices(cls, indices, values):
        if "original_image_size" not in values:
            raise ValueError("original_image_size is not defined")
        for index in indices:
            if len(index) != 2:
                raise ValueError("indices must be a list of pairs")
            inside = (
                0 <= index[0] < values["original_image_size"][0]
                and 0 <= index[1] < values["original_image_size"][1]
            )
            if not inside:
                raise ValueError("indices must be inside the original image")
        return indices
