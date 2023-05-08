from abc import ABC, abstractmethod

import numpy as np

from settings_model import SettingsModel


class BaseROI(SettingsModel, ABC):
    """Base class for regions of interest inside an image.

    Attributes:
        original_image_size: The size of the original image as (width, height)
    """

    original_image_size: tuple[int, int]

    @property
    @abstractmethod
    def mask(self) -> np.ndarray:
        """A boolean array with the same shape as the original image.

        True values indicate that the pixel is part of the region of interest."""

        raise NotImplementedError()
