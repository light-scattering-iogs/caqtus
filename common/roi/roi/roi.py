from abc import ABC, abstractmethod

from settings_model import SettingsModel, Field


class RegionOfInterest(SettingsModel, ABC):
    original_image_size: tuple[int, int] = Field(
        description="The size of the original image as (width, height)"
    )

    @property
    @abstractmethod
    def roi_indices(self) -> tuple[tuple[int, int], ...]:
        """The indices of the pixels in the original image that are part of the region of interest"""
        ...


class ArbitraryShapedRegionOfInterest(RegionOfInterest):
    roi_indices: tuple[tuple[int, int], ...] = Field(
        description="The indices of the pixels in the original image that are part of the region of interest"
    )

    @property
    def roi_indices(self) -> tuple[tuple[int, int], ...]:
        return self.roi_indices
