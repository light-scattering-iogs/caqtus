from abc import ABC, abstractmethod
from functools import cached_property
from typing import Self

import numpy as np

from settings_model import SettingsModel, Field


class RegionOfInterest(SettingsModel, ABC):
    original_image_size: tuple[int, int] = Field(
        description="The size of the original image as (width, height)"
    )

    @property
    @abstractmethod
    def indices(self) -> tuple[tuple[int, int], ...]:
        """The indices of the pixels in the original image that are part of the region of interest"""
        ...

    @cached_property
    def mask(self):
        """A boolean array with the same shape as the original image.

        True values indicate that the pixel is part of the region of interest."""
        mask = np.full(self.original_image_size, False)
        mask[*np.array(self.indices).T] = True
        return mask


class ArbitraryShapedRegionOfInterest(RegionOfInterest):
    roi_indices: tuple[tuple[int, int], ...] = Field(
        description="The indices of the pixels in the original image that are part of the region of interest",
        allow_mutation=False
    )

    @property
    def indices(self) -> tuple[tuple[int, int], ...]:
        return self.roi_indices

    @classmethod
    def from_mask(cls, mask: np.ndarray) -> Self:
        """Create a region of interest from a mask

        Args:
            mask: A boolean array with the same shape as the original image. True values indicate that the pixel is part
            of the region of interest.
        """
        return cls(original_image_size=mask.shape, roi_indices=np.argwhere(mask).tolist())
