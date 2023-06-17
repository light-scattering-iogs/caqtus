from numbers import Real
from typing import TypeVar, NewType, Any, TypeGuard

import numpy as np

from data_types import DataLabel, is_data_label

Width = TypeVar("Width", bound=int)
Height = TypeVar("Height", bound=int)

T = TypeVar("T", bound=Real)

Image = np.ndarray[tuple[Width, Height], np.dtype[T]]

ImageLabel = NewType("ImageLabel", DataLabel)


def is_image(image: Any) -> TypeGuard[Image]:
    """Check if image has a valid image type."""

    return isinstance(image, np.ndarray) and image.ndim == 2


def is_image_label(label: Any) -> TypeGuard[ImageLabel]:
    """Check if label has a valid image label type."""

    return is_data_label(label)
