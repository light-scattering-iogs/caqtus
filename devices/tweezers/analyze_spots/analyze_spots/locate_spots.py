from typing import Literal

import numpy as np
import cv2


def locate_spots(
    image: np.ndarray, threshold: float, connectivity: Literal[4, 8] = 8
) -> list[tuple[float, float]]:
    """Locate spots in an image.

    Args:
        image: Image to locate spots in.
        threshold: Threshold to use for binarization.
        connectivity: Connectivity (ie, number of neighbors) to use for connected components analysis.

    Returns:
        List of centroids of spots in the image. Note that the values below the threshold are not included.
    """
    # noinspection PyUnresolvedReferences
    _, binary_image = cv2.threshold(image, threshold, 1, cv2.THRESH_BINARY)
    number_components, labeled_image, _, centroids = cv2.connectedComponentsWithStats(
        binary_image.astype(np.uint8), connectivity=connectivity
    )
    centroids = [(x, y) for y, x in centroids.tolist()]

    background = (binary_image == 0)
    background_labels = np.unique(labeled_image[background])
    if len(background_labels) > 1:
        raise ValueError("The background is not a single connected component.")
    if len(background_labels) == 1:
        del centroids[background_labels[0]]
    return sorted(centroids)
