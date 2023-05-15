from typing import Generic

import numpy as np

from atom_detector.configuration import AtomLabel
from device.runtime import RuntimeDevice, Field
from single_atom_detector import SingleAtomDetector


class AtomDetector(RuntimeDevice, Generic[AtomLabel]):
    """Pseudo device that can detect the presence of atoms in an image.

    Attributes:
        single_atom_detectors: A dictionary of single atom detectors. The keys are the atom labels and the values are
            the single atom detectors. All detectors must be able to handle the same image shape. Mutating this
            attribute during the detector lifetime is prohibited.
    """

    single_atom_detectors: dict[AtomLabel, SingleAtomDetector] = Field(
        allow_mutation=False
    )

    def initialize(self) -> None:
        super().initialize()

    def update_parameters(self, **kwargs) -> None:
        raise RuntimeError(
            "Atom detector has no parameters that can be updated during its lifetime."
        )

    def are_atoms_present(self, image: np.ndarray) -> dict[AtomLabel, bool]:
        """Return whether atoms are present in the image.

        Args:
            image: The image to analyze.

        Returns:
            A dictionary of booleans indicating whether atoms are present in the image for each atom label.
        """

        return {
            atom_label: single_atom_detector.is_atom_present(image)
            for atom_label, single_atom_detector in self.single_atom_detectors.items()
        }
