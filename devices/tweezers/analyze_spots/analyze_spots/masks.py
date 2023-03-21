import numpy as np


def circular_mask(image, center: tuple[float, float], radius: float) -> np.ndarray[bool]:
    """Create a circular mask for an image.

    Args:
        image: Image to create a mask for.
        center: Center of the circle.
        radius: Radius of the circle.

    Returns:
        Mask for the image. This is a boolean array with the same shape as the image. The mask is True outside the
        circle and False inside.
    """

    x, y = np.meshgrid(
        np.arange(image.shape[0]), np.arange(image.shape[1]), indexing="ij"
    )
    mask = (x - center[0]) ** 2 + (y - center[1]) ** 2 > radius**2
    return mask
