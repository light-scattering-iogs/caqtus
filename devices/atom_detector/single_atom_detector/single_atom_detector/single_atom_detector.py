import numpy as np

from settings_model import YAMLSerializable
from util import attrs
from .atom_signal_calculator import WeightedAtomSignalCalculator


@attrs.define(slots=False)
class SingleAtomDetector:
    """Look at an image and determine whether one specific atom is present."""

    atom_signal_calculator: WeightedAtomSignalCalculator = attrs.field(
        validator=attrs.validators.instance_of(WeightedAtomSignalCalculator),
        on_setattr=attrs.setters.validate,
    )
    threshold: float = attrs.field(
        converter=float,
        on_setattr=attrs.setters.convert,
    )

    def is_atom_present(self, image: np.ndarray) -> bool:
        """Determine whether the associated atom is present in the image"""

        return self.compute_signal(image) > self.threshold

    def compute_signal(self, image: np.ndarray) -> float:
        """Compute the signal for the associated atom in the image."""

        return self.atom_signal_calculator.compute_signal(image)


YAMLSerializable.register_attrs_class(SingleAtomDetector)
