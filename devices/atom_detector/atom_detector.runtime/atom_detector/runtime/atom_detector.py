import numpy as np

from atom_detector.configuration import (
    AtomLabel,
    ImagingConfigurationName,
    ImagingConfiguration,
)
from device.runtime import RuntimeDevice, Field
from image_types import Image


class AtomDetector(RuntimeDevice):
    """Pseudo device that can detect the presence of atoms in an image."""

    imaging_configurations: dict[
        ImagingConfigurationName, ImagingConfiguration
    ] = Field(allow_mutation=False)

    def initialize(self) -> None:
        super().initialize()

    def update_parameters(self, **kwargs) -> None:
        raise RuntimeError(
            "Atom detector has no parameters that can be updated during its lifetime."
        )

    def are_atoms_present(
        self, image: Image, imaging_config: ImagingConfigurationName
    ) -> dict[AtomLabel, bool]:
        """Return whether atoms are present in the image.

        Args:
            image: The image to analyze.
            imaging_config: The imaging configuration to use to detect the atoms.

        Returns:
            A dictionary of booleans indicating whether atoms are present in the image for each atom label.
        """

        single_atom_detectors = self.imaging_configurations[imaging_config]

        return {
            atom_label: single_atom_detector.is_atom_present(image)
            for atom_label, single_atom_detector in single_atom_detectors.items()
        }

    def compute_signals(
        self, image: np.ndarray, imaging_config: ImagingConfigurationName
    ) -> dict[AtomLabel, float]:
        """Return the signal for each atom label.

        Args:
            image: The image to analyze.

        Returns:
            A dictionary of signals for each atom label.
        """

        single_atom_detectors = self.imaging_configurations[imaging_config]

        return {
            atom_label: single_atom_detector.compute_signal(image)
            for atom_label, single_atom_detector in single_atom_detectors.items()
        }

    def get_traps_labels(
        self, imaging_configuration: ImagingConfigurationName
    ) -> set[AtomLabel]:
        """Return the labels of all the traps."""

        single_atom_detectors = self.imaging_configurations[imaging_configuration]

        return set(single_atom_detectors.keys())
