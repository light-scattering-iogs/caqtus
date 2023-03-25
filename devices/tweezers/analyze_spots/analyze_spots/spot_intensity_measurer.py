from typing import Callable

import numpy as np

from .masks import circular_mask
from .locate_spots import locate_spots


class SpotAnalyzer:
    """Computes the intensities of spots in an image."""

    def __init__(self):
        self._centroids: list[tuple[float, float]] = []
        self._masks: list[np.ndarray] = []

    def register_regions_of_interest(
        self, reference_image: np.ndarray, relative_threshold: float, radius: float
    ) -> np.ndarray:
        """Register the regions of interest in the image for each spot.

        This object can only measure the intensity if regions of interest have been registered once previously.
        It makes no assumption about the disposition of the spots in the image.

        Args:
            reference_image: The image to use to locate the spots
            relative_threshold: The threshold to use to locate the spots, as a fraction of the maximum value in the
            image.
            radius: The radius of the region of interest around each spot

        Returns:
            The masked image, with the values outside the regions of interest masked out
        """
        self._centroids = locate_spots(
            reference_image, threshold=np.max(reference_image) * relative_threshold
        )
        self._masks = [
            np.logical_not(circular_mask(reference_image, trap_center, radius))
            for trap_center in self._centroids
        ]

        mask_union = np.logical_or.reduce(self._masks)
        return np.ma.masked_array(reference_image, np.logical_not(mask_union))

    def compute_intensity(
        self, image: np.ndarray, method: Callable[[np.ndarray], float] = np.mean
    ) -> list[float]:
        """Compute the intensity of each spot in the image.

        Args:
            image: The image to use to compute the intensity
            method: The function to use to compute the intensity, defaults to the mean

        Returns:
            The intensity of each spot in the image. The (random) order of the intensities is the same as the order of
            the spots found in the image.
        """

        intensities = [method(image[mask]) for mask in self._masks]
        return intensities

    @property
    def number_spots(self) -> int:
        return len(self._centroids)


class GridSpotAnalyzer(SpotAnalyzer):
    """Computes the intensities of spots in an image, assuming that the spots are arranged in a grid."""

    def __init__(self, number_rows: int, number_columns: int):
        super().__init__()
        self._number_rows = number_rows
        self._number_columns = number_columns
        self._indices: list[tuple[int, int]] = []

    def register_regions_of_interest(
        self, reference_image: np.ndarray, relative_threshold: float, radius: float
    ) -> np.ndarray:
        result = super().register_regions_of_interest(
            reference_image, relative_threshold, radius
        )

        if len(self._centroids) != self._number_rows * self._number_columns:
            raise ValueError(
                f"Expected {self._number_rows * self._number_columns} spots, found {len(self._centroids)}"
            )

        def sort_along_x(value):
            index_, (x, y) = value
            return x

        def sort_along_y(value):
            index_, (x, y) = value
            return y

        centroids = sorted(enumerate(self._centroids), key=sort_along_x)

        rows = [
            centroids[self._number_columns * row: self._number_columns * (row + 1)]
            for row in range(self._number_rows)
        ]
        for row in rows:
            row.sort(key=sort_along_y)

        self._indices = []

        for row_number, row in enumerate(rows):
            for column_number, (index, _) in enumerate(row):
                self._indices.append((row_number, column_number))
        return result

    def compute_intensity(
        self, image: np.ndarray, method: Callable[[np.ndarray], float] = np.mean
    ) -> np.ndarray[float]:
        intensities = super().compute_intensity(image, method=method)
        matrix_intensities = np.zeros(
            (self._number_rows, self._number_columns), dtype=float
        )
        for index, (row, column) in enumerate(self._indices):
            matrix_intensities[row, column] = intensities[index]
        return matrix_intensities
