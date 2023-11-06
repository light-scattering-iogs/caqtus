from typing import Self, Iterable, SupportsFloat

import numpy as np

from roi import ArbitraryROI
from settings_model import YAMLSerializable
from util import attrs, serialization


@attrs.define(slots=False)
class WeightedAtomSignalCalculator:
    """Compute an analog value indicating the potential presence of a specific atom in
    an image.

    To compute the signal of an atom in an image, the image is multiplied by a weighted
    map and the sum of the resulting values is computed. An offset can be removed to the
    signal to account for the background.

    Note that objects of this class don't perform thresholding, since sometimes we want
    to look at the analog signal itself.

    Fields:
        roi: The ROI to use to compute the signal
        weights: The weights to use to compute the signal. It must have the same length
        as the ROI. The pixel at roi.indices[i] will be multiplied by weights[i] to
        compute the signal.
    """

    roi: ArbitraryROI = attrs.field(
        validator=attrs.validators.instance_of(ArbitraryROI),
        on_setattr=attrs.setters.frozen,
    )
    weights: tuple[float, ...] = attrs.field(
        converter=tuple,
        validator=attrs.validators.deep_iterable(
            member_validator=attrs.validators.instance_of(float),
            iterable_validator=attrs.validators.instance_of(tuple),
        ),
        on_setattr=attrs.setters.frozen,
    )
    offset: float = attrs.field(
        converter=float,
        on_setattr=attrs.setters.convert,
    )

    _x: np.ndarray = attrs.field(init=False, eq=False)
    _y: np.ndarray = attrs.field(init=False, eq=False)
    _weights_np: np.ndarray = attrs.field(init=False, eq=False)

    def __attrs_post_init__(self):
        self._weights_np = np.array(self.weights)
        self._x = np.array([x for x, _ in self.roi.indices])
        self._y = np.array([y for _, y in self.roi.indices])

    def compute_signal(self, image: np.ndarray) -> float:
        """Compute the signal for each atom in the image"""

        return float(np.sum(image[self._x, self._y] * self._weights_np)) - self.offset

    def compute_signals(self, images: Iterable[np.ndarray]) -> list[float]:
        """Compute the signal for each atom in each image in the iterable"""

        return [self.compute_signal(image) for image in images]

    def to_weighted_map(self):
        """Return the weighted map used to compute the signal"""

        indices = np.array(self.roi.indices)
        mask = np.full(self.roi.original_image_size, True)
        mask[indices[:, 0], indices[:, 1]] = False
        weighted_image = np.ma.MaskedArray(
            np.zeros(self.roi.original_image_size), mask=mask
        )
        weighted_image[indices[:, 0], indices[:, 1]] = self.weights
        return weighted_image

    @classmethod
    def from_weighted_map(
        cls, weighted_map: np.ma.MaskedArray, offset: SupportsFloat = 0.0
    ) -> Self:
        """Create a WeightedAtomSignalCalculator from a weighted map.

        A weighted map is a masked array where the mask is True for pixels that are not
        part of the ROI and False for pixels that are part of the ROI. The values in the
        array that are not masked are the weights to use to compute the signal. This
        method will create a WeightedAtomSignalCalculator from the weighted map with
        the correct roi and weights.
        """

        if not isinstance(weighted_map, np.ma.MaskedArray):
            raise TypeError(
                f"weighted_map must be a masked array, not {type(weighted_map)}"
            )
        if weighted_map.ndim != 2:
            raise ValueError(
                f"weighted_map must be a 2D image , not {weighted_map.ndim}D"
            )

        roi = ArbitraryROI.from_mask(np.logical_not(weighted_map.mask))
        weights = weighted_map[*np.array(roi.indices).T].tolist()
        return cls(roi=roi, weights=weights, offset=offset)


serialization.customize(
    _x=serialization.AttributeOverride(omit=True),
    _y=serialization.AttributeOverride(omit=True),
    _weights_np=serialization.AttributeOverride(omit=True),
)(WeightedAtomSignalCalculator)


YAMLSerializable.register_attrs_class(WeightedAtomSignalCalculator)
