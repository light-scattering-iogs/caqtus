from collections.abc import Iterable
from typing import Self

import attrs
import numpy as np

from .roi import ROI, Width, Height


@attrs.define
class ArbitraryROI(ROI):
    """Arbitrary region of interest inside an image.

    This ROI is defined by specifying the indices of the pixels in the original image
    that are part of the region of interest.

    While this ROI is the most generic one, it becomes very inefficient when the number
    of pixels in the region of interest is large, because it stores the coordinates of
    all pixels.
    Whenever possible, use a more specific ROI.

    Attributes:
        indices: The indices of the pixels in the original image that are part of the
        region of interest.
    """

    indices: tuple[tuple[int, int], ...] = attrs.field(
        converter=tuple,
        on_setattr=attrs.setters.pipe(attrs.setters.convert, attrs.setters.validate),
    )

    def get_indices(self) -> tuple[Iterable[int], Iterable[int]]:
        indices = np.array(self.indices).T
        return indices[0], indices[1]

    @classmethod
    def from_mask(cls, mask: np.ndarray) -> Self:
        """Create a region of interest from a mask

        Args:
            mask: A boolean array with the same shape as the original image.
            True values indicate that the pixel is part of the region of interest.
        """

        shape = mask.shape
        if len(shape) != 2:
            raise ValueError("mask must be 2D")
        shape = Width(shape[0]), Height(shape[1])
        indices = np.argwhere(mask).tolist()
        return cls(
            original_image_size=shape, indices=tuple(tuple(index) for index in indices)
        )

    @indices.validator  # type: ignore
    def validate_indices(self, _, indices):
        for index in indices:
            if not isinstance(index, tuple):
                raise ValueError("indices must be a list of tuples")
            if len(index) != 2:
                raise ValueError("indices must be a list of pairs")
            inside = (
                0 <= index[0] < self.original_image_size[0]
                and 0 <= index[1] < self.original_image_size[1]
            )
            if not inside:
                raise ValueError("indices must be inside the original image")
        return indices
