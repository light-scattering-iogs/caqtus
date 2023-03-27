from abc import ABC, abstractmethod

from settings_model import SettingsModel, Field


class RegionOfInterest(SettingsModel, ABC):
    original_image_size: tuple[int, int] = Field(
        description="The size of the original image as (width, height)"
    )

    @property
    @abstractmethod
    def roi_indices(self) -> np.ndarray:
        ...
