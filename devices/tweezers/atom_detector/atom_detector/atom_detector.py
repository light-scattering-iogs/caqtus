from numbers import Number
from typing import Self

import numpy as np
import yaml

from settings_model import YAMLSerializable
from .atom_signal_calculator import WeightedAtomSignalCalculator


class AtomDetector(YAMLSerializable):
    """Look at an image and determine whether a specific atom is present

    Objects of this class are associated with a specific atom. User code should refrain from accessing the private
    members of this class since the way atoms are detected may change.
    """

    def __init__(self, atom_signal_calculator: WeightedAtomSignalCalculator, threshold: float):
        if not isinstance(atom_signal_calculator, WeightedAtomSignalCalculator):
            raise TypeError(
                f"atom_signal_calculator must be an AtomSignalCalculator, not {type(atom_signal_calculator)}"
            )
        if not isinstance(threshold, Number):
            raise TypeError(f"threshold must be a number, not {type(threshold)}")
        self._atom_signal_calculator = atom_signal_calculator
        self._threshold = float(threshold)

    def is_atom_present(self, image: np.ndarray) -> bool:
        """Determine whether the associated atom is present in the image"""

        return self.compute_signal(image) > self._threshold

    def compute_signal(self, image: np.ndarray) -> float:
        """Compute the signal for the associated atom in the image."""

        return self._atom_signal_calculator.compute_signal(image)

    @classmethod
    def representer(cls, dumper: yaml.Dumper, settings: Self):
        """Return a yaml representation of the object"""

        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {
                "atom_signal_calculator": settings._atom_signal_calculator,
                "threshold": settings._threshold,
            },
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        """Construct an object from a yaml node"""

        kwargs = loader.construct_mapping(node, deep=True)
        return cls(**kwargs)
