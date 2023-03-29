from typing import Self

import numpy as np
import yaml

from roi import ArbitraryShapedRegionOfInterest
from settings_model import YAMLSerializable


class AtomSignalCalculator(YAMLSerializable):
    """Compute an analog value indicating the potential presence of a specific atom in an image

    Note that objects of this class don't perform thresholding, since sometimes we want to look at the raw signal. User
    code should refrain from accessing the private members of this class since the way atoms are detected may change.
    """

    def __init__(self, weighted_image: np.ma.MaskedArray):
        self._roi = ArbitraryShapedRegionOfInterest.from_mask(
            np.logical_not(weighted_image.mask)
        )
        self._weights: list[float] = weighted_image[
            *np.array(self._roi.indices).T
        ].tolist()
        self._weighed_image = weighted_image

    def compute_signal(self, image: np.ndarray) -> float:
        """Compute the signal for each atom in the image"""

        return float(np.sum(image * self._weighed_image))

    @classmethod
    def representer(cls, dumper: yaml.Dumper, atomic_signal_calculator: Self):
        """Return a yaml representation of the object"""

        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {
                "roi": atomic_signal_calculator._roi,
                "weights": atomic_signal_calculator._weights,
            },
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        """Construct an object from a yaml node"""

        kwargs = loader.construct_mapping(node, deep=True)
        roi: ArbitraryShapedRegionOfInterest = kwargs["roi"]
        weights = kwargs["weights"]

        indices = np.array(roi.indices)
        mask = np.full(roi.original_image_size, True)
        mask[indices[:, 0], indices[:, 1]] = False
        weighted_image = np.ma.MaskedArray(np.zeros(roi.original_image_size), mask=mask)
        weighted_image[indices[:, 0], indices[:, 1]] = weights
        return cls(weighted_image)
