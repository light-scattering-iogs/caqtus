import copy
from itertools import chain
from typing import Callable, Sequence

import numpy as np

from roi import ROI, ArbitraryROI
from .locate_spots import locate_spots
from .masks import circular_mask

EvaluationFunction = Callable[[np.ma.MaskedArray], float]


class SpotAnalyzer:
    """Computes the intensities of spots in an image."""

    def __init__(self):
        self._centroids: list[tuple[float, float]] = []
        self._rois: list[ROI] = []

    @property
    def centroids(self) -> list[tuple[float, float]]:
        return copy.deepcopy(self._centroids)

    def register_regions_of_interest(
        self, reference_image: np.ndarray, *, relative_threshold: float, radius: float
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
        masks = [
            np.logical_not(circular_mask(reference_image, trap_center, radius))
            for trap_center in self._centroids
        ]
        self._rois = [ArbitraryROI.from_mask(mask) for mask in masks]

        mask_union = np.logical_or.reduce(masks)
        return np.ma.masked_array(reference_image, np.logical_not(mask_union))

    def compute_intensity(
        self,
        image: np.ndarray,
        method: EvaluationFunction | Sequence[EvaluationFunction] = np.mean,
    ) -> list[float]:
        """Compute the intensity of each spot in the image.

        Args:
            image: The image to use to compute the intensity
            method: The function to use to compute the intensity, defaults to the mean

        Returns:
            The intensity of each spot in the image. The (random) order of the intensities is the same as the order of
            the spots found in the image.
        """
        if not isinstance(method, Sequence):
            method = [method] * self.number_spots

        if len(method) != self.number_spots:
            raise ValueError(
                f"Expected {self.number_spots} methods, found {len(method)}"
            )

        intensities = []
        for roi, method in zip(self._rois, method):
            masked_image = np.ma.masked_array(image, np.logical_not(roi.get_mask()))
            intensities.append(method(masked_image))
        return intensities

    @property
    def number_spots(self) -> int:
        return len(self._centroids)

    @property
    def rois(self) -> list[ROI]:
        return copy.deepcopy(self._rois)


class GridSpotAnalyzer(SpotAnalyzer):
    """Computes the intensities of spots in an image, assuming that the spots are arranged in a grid."""

    def __init__(self, number_rows: int, number_columns: int):
        super().__init__()
        self._number_rows = number_rows
        self._number_columns = number_columns
        self._coordinates: list[tuple[int, int]] = []

    @property
    def number_rows(self) -> int:
        return self._number_rows

    @property
    def number_columns(self) -> int:
        return self._number_columns

    def register_regions_of_interest(
        self, reference_image: np.ndarray, *, relative_threshold: float, radius: float
    ) -> np.ndarray:
        result = super().register_regions_of_interest(
            reference_image, relative_threshold=relative_threshold, radius=radius
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

        columns = [
            centroids[self._number_rows * column : self._number_rows * (column + 1)]
            for column in range(self._number_columns)
        ]

        for column in columns:
            column.sort(key=sort_along_y)

        ordered_indices = list(chain.from_iterable(columns))

        self._centroids = [self._centroids[index] for index, _ in ordered_indices]
        self._rois = [self._rois[index] for index, _ in ordered_indices]
        self._coordinates = [self.coordinates(index) for index, _ in ordered_indices]
        return result

    def compute_intensity_matrix(
        self, image: np.ndarray, method: EvaluationFunction = np.mean
    ) -> np.ndarray[float]:
        intensities = super().compute_intensity(image, method=method)
        matrix_intensities = np.zeros(
            (self._number_columns, self._number_rows), dtype=float
        )
        for index, (column, row) in enumerate(self._coordinates):
            matrix_intensities[column, row] = intensities[index]
        return matrix_intensities

    def row(self, index: int):
        return index % self._number_rows

    def column(self, index: int):
        return index // self._number_rows

    def x(self, index: int) -> int:
        return self.column(index)

    def y(self, index: int) -> int:
        return self.row(index)

    def coordinates(self, index: int) -> tuple[int, int]:
        return self.x(index), self.y(index)
