from numbers import Real
from typing import Self, Iterable, Sequence, SupportsFloat

import numpy as np
import yaml

from roi import ArbitraryROI
from settings_model import YAMLSerializable


class WeightedAtomSignalCalculator(YAMLSerializable):
    """Compute an analog value indicating the potential presence of a specific atom in an image

    To compute the signal of an atom in an image, the image is multiplied by a weighted map and the sum of the resulting
    values is computed. An offset can be removed to the signal to account for the background.

    Note that objects of this class don't perform thresholding, since sometimes we want to look at the raw signal. User
    code should refrain from accessing the private members of this class since the way atoms are detected may change.
    """

    def __init__(
        self,
        roi: ArbitraryROI,
        weights: Sequence[float],
        offset: SupportsFloat = 0.0,
    ):
        """Create a new weighted atom signal calculator

        Args:
            roi: The ROI to use to compute the signal
            weights: The weights to use to compute the signal. It must have the same length as the ROI. The pixel at
            roi.indices[i] will be multiplied by weights[i] to compute the signal.
        """

        self._weights = list(weights)
        self._roi = roi
        self._weights_np = np.array(self._weights)
        self.offset = float(offset)
        self._x = np.array([x for x, _ in self._roi.indices])
        self._y = np.array([y for _, y in self._roi.indices])

    def compute_signal(self, image: np.ndarray) -> float:
        """Compute the signal for each atom in the image"""

        return float(np.sum(image[self._x, self._y] * self._weights_np)) - self.offset

    def compute_signals(self, images: Iterable[np.array]) -> list[float]:
        """Compute the signal for each atom in each image in the iterable"""

        return [self.compute_signal(image) for image in images]

    @property
    def offset(self) -> float:
        """Return the offset of the signal"""
        return self._offset

    @offset.setter
    def offset(self, offset: Real):
        """Set the offset of the signal"""

        if not isinstance(offset, Real):
            raise TypeError(f"offset must be a real number, not {type(offset)}")
        self._offset = float(offset)

    def to_weighted_map(self):
        """Return the weighted map used to compute the signal"""

        indices = np.array(self._roi.indices)
        mask = np.full(self._roi.original_image_size, True)
        mask[indices[:, 0], indices[:, 1]] = False
        weighted_image = np.ma.MaskedArray(
            np.zeros(self._roi.original_image_size), mask=mask
        )
        weighted_image[indices[:, 0], indices[:, 1]] = self._weights

    @classmethod
    def from_weighted_map(
        cls, weighted_map: np.ma.MaskedArray, offset: SupportsFloat = 0.0
    ) -> Self:
        """Set the weighted map used to compute the signal"""

        if not isinstance(weighted_map, np.ma.MaskedArray):
            raise TypeError(
                f"weighted_map must be a masked array, not {type(weighted_map)}"
            )
        if weighted_map.ndim != 2:
            raise ValueError(f"weighted_map must be 2D, not {weighted_map.ndim}D")

        roi = ArbitraryROI.from_mask(np.logical_not(weighted_map.mask))
        weights: list[float] = weighted_map[*np.array(roi.indices).T].tolist()
        return cls(roi, weights, offset)

    @classmethod
    def representer(cls, dumper: yaml.Dumper, atomic_signal_calculator: Self):
        """Return a yaml representation of the object"""

        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {
                "roi": atomic_signal_calculator._roi,
                "weights": atomic_signal_calculator._weights,
                "offset": atomic_signal_calculator.offset,
            },
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        """Construct an object from a yaml node"""

        return cls(**loader.construct_mapping(node, deep=True))

    def __eq__(self, other):
        if not isinstance(other, WeightedAtomSignalCalculator):
            return False
        return (
            self._roi == other._roi
            and self._weights == other._weights
            and self._offset == other._offset
        )
