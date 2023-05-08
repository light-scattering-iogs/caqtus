import uuid
from numbers import Real
from typing import Self, Optional, Any

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
        weighted_map: np.ma.MaskedArray,
        offset: Real = 0,
        label: Optional[Any] = None,
    ):
        """Create a new weighted atom signal calculator

        Args:
            weighted_map: A masked array with the same shape as the original image. When computing the signal, only the
                values that are not masked are used.
            label: An optional label that can be used to identify the atom associated with this object. If None, it will
                generate a unique label.

        """

        if label is None:
            label = uuid.uuid4()

        self.weighted_map = weighted_map

        self._label = label
        self.offset = offset

    def compute_signal(self, image: np.ndarray) -> float:
        """Compute the signal for each atom in the image"""

        return float(np.sum(image * self._weighed_image)) - self.offset

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

    @property
    def weighted_map(self):
        """Return the weighted map used to compute the signal"""
        return self._weighed_image

    @weighted_map.setter
    def weighted_map(self, weighted_map: np.ma.MaskedArray):
        """Set the weighted map used to compute the signal"""

        if not isinstance(weighted_map, np.ma.MaskedArray):
            raise TypeError(
                f"weighted_map must be a masked array, not {type(weighted_map)}"
            )
        if weighted_map.ndim != 2:
            raise ValueError(f"weighted_map must be 2D, not {weighted_map.ndim}D")

        self._roi = ArbitraryROI.from_mask(
            np.logical_not(weighted_map.mask)
        )
        self._weights: list[float] = weighted_map[
            *np.array(self._roi.indices).T
        ].tolist()
        self._weighed_image = weighted_map

    @classmethod
    def representer(cls, dumper: yaml.Dumper, atomic_signal_calculator: Self):
        """Return a yaml representation of the object"""

        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {
                "roi": atomic_signal_calculator._roi,
                "weights": atomic_signal_calculator._weights,
                "label": str(atomic_signal_calculator._label),
                "offset": atomic_signal_calculator.offset,
            },
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        """Construct an object from a yaml node"""

        kwargs = loader.construct_mapping(node, deep=True)
        roi: ArbitraryROI = kwargs["roi"]
        weights = kwargs["weights"]
        offset = kwargs["offset"]

        indices = np.array(roi.indices)
        mask = np.full(roi.original_image_size, True)
        mask[indices[:, 0], indices[:, 1]] = False
        weighted_image = np.ma.MaskedArray(np.zeros(roi.original_image_size), mask=mask)
        weighted_image[indices[:, 0], indices[:, 1]] = weights
        return cls(weighted_image, offset, uuid.UUID(kwargs["label"]))
