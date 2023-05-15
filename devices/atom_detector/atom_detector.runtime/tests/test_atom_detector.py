import numpy as np

from atom_detector.runtime import AtomDetector


def test_atom_detector():

    detector = AtomDetector[int](name="detector", single_atom_detectors={})

    with detector:
        detector.are_atoms_present(image=np.zeros((100, 100)))
