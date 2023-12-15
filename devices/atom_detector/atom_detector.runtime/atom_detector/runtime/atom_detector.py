from __future__ import annotations

import numpy as np
from atom_detector.configuration import (
    AtomLabel,
    ImagingConfigurationName,
    ImagingConfiguration,
)
from attrs import define, field
from attrs.setters import frozen
from device.runtime import RuntimeDevice
from image_types import Image
from single_atom_detector import SingleAtomDetector

from util import attrs


@define(slots=False)
class AtomDetector(RuntimeDevice):
    """Pseudo device that can detect the presence of atoms in an image."""

    imaging_configurations: dict[
        ImagingConfigurationName, ImagingConfiguration
    ] = field(on_setattr=frozen)

    @imaging_configurations.validator  # type: ignore
    def _validate_imaging_configurations(self, _, value):
        if not isinstance(value, dict):
            raise TypeError("imaging_configurations must be a dict.")
        for imaging_configuration in value.values():
            if not isinstance(imaging_configuration, dict):
                raise TypeError(
                    "imaging_configurations must be a dict of dict of SingleAtomDetector."
                )
            for single_atom_detector in imaging_configuration.values():
                if not isinstance(single_atom_detector, SingleAtomDetector):
                    raise TypeError(
                        "imaging_configurations must be a dict of dict of SingleAtomDetector."
                    )

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
            imaging_config: The imaging configuration to use to detect the atoms.

        Returns:
            A dictionary of signals for each atom label.
        """

        single_atom_detectors = self.imaging_configurations[imaging_config]

        return {
            atom_label: single_atom_detector.compute_signal(image)
            for atom_label, single_atom_detector in single_atom_detectors.items()
        }

    def analyze_image(
        self, image: np.ndarray, imaging_config: ImagingConfigurationName
    ) -> AtomAnalysisResult:
        single_atom_detectors = self.imaging_configurations[imaging_config]

        fluorescence_signals = {
            atom_label: single_atom_detector.compute_signal(image)
            for atom_label, single_atom_detector in single_atom_detectors.items()
        }
        atom_presences = {
            atom_label: single_atom_detector.is_atom_present(image)
            for atom_label, single_atom_detector in single_atom_detectors.items()
        }
        return AtomAnalysisResult(
            imaging_config=imaging_config,
            signals=fluorescence_signals,
            atoms_presences=atom_presences,
        )

    def get_traps_labels(
        self, imaging_configuration: ImagingConfigurationName
    ) -> set[AtomLabel]:
        """Return the labels of all the traps."""

        single_atom_detectors = self.imaging_configurations[imaging_configuration]

        return set(single_atom_detectors.keys())

    @classmethod
    def exposed_remote_methods(cls) -> tuple[str, ...]:
        return super().exposed_remote_methods() + (
            "get_traps_labels",
            "compute_signals",
            "are_atoms_present",
            "analyze_image",
        )


@attrs.frozen
class AtomAnalysisResult:
    """Contains information obtained when looking for the presence of atoms in an image.

    Fields:
        imaging_config: The name of the imaging configuration that was used to analyze the image.
        signals: A dictionary of fluorescence signals for each atom label.
        atoms_presences: A dictionary of booleans indicating whether atoms are present in the image for each atom label.
    """

    imaging_config: ImagingConfigurationName
    fluorescence_signals: dict[AtomLabel, float]
    atom_presences: dict[AtomLabel, bool]
