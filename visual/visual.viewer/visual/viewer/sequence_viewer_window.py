from functools import cache

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QDockWidget
from analyza.loading.importers import (
    import_parameters,
    break_namespaces,
    split_units,
    array_as_float,
    import_measures,
    import_time,
)

from atom_detector.runtime import AtomDetector
from experiment.session import get_standard_experiment_session
from sequence.runtime import Sequence
from .curve_plotter import CurveViewerWidget
from .image_viewer import ImageViewerWidget
from .sequence_viewer import SignalingSequenceWatcher


@cache
def get_atom_detector(sequence: Sequence) -> AtomDetector:
    session = get_standard_experiment_session()
    with session.activate():
        detector_config = sequence.get_experiment_config(session).get_device_config(
            "Atom detector"
        )
        return AtomDetector(
            name="detector", **detector_config.get_device_init_args("5x5 tweezers")
        )


def mot_signal_importer(shot, session):
    parameters = (import_parameters | break_namespaces | split_units)(
        shot, session
    ) | import_time(shot, session)
    data = (import_measures | array_as_float)(shot, session)
    image = data["Orca Quest.picture"] - data["Orca Quest.background"]

    mot_roi = (slice(34, 84), slice(34, 84))
    signal = np.sum(image[mot_roi]) * 0.11
    return {**parameters, "signal": signal}


def tweezer_importer(shot, session):
    parameters = (import_parameters | break_namespaces | split_units)(
        shot, session
    ) | import_time(shot, session)
    data = (import_measures | array_as_float)(shot, session)
    detector = get_atom_detector(shot.sequence)
    atoms = detector.are_atoms_present(data["Orca Quest.picture 1"])
    n1 = sum(atoms.values())
    atoms = detector.are_atoms_present(data["Orca Quest.picture 2"])
    n2 = sum(atoms.values())
    d = {f'survival': n2 / n1}
    return {**parameters, **d}


def average_tweezer_fluo(shot, session):
    parameters = (import_parameters | break_namespaces | split_units)(
        shot, session
    ) | import_time(shot, session)
    data = (import_measures | array_as_float)(shot, session)
    image = data["Orca Quest.picture"]  # - data["Orca Quest.background"]

    t = range(25)
    signals = [traps[i].compute_signal(image) for i in t]
    point = np.mean(signals)
    return {**parameters, **{"signal": point}}


def image_importer(label: str):
    def importer(shot, session):
        data = (import_measures | array_as_float)(shot, session)
        image = data[f"Orca Quest.{label}"]  # - data["Orca Quest.background"]
        return {"image": image}

    return importer


class SequenceViewerWindow(QMainWindow):
    def __init__(self):
        sequence = Sequence("2023.07_July.07.test2")
        super().__init__()
        sequence_watcher = SignalingSequenceWatcher(
            sequence=sequence,
            importer=tweezer_importer,
            # importer=image_importer("picture"),
            watch_interval=0.1,
            chunk_size=20,
        )
        detector = get_atom_detector(sequence)

        image_viewer = ImageViewerWidget(
            sequence_watcher, importer=image_importer("picture"), image_label="image"
        )
        dock_widget = QDockWidget("Image viewer", self)
        dock_widget.setWidget(image_viewer)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_widget)

        # image_viewer = ImageViewerWidget(
        #     sequence_watcher, importer=image_importer("picture 3"), image_label="image"
        # )
        dock_widget = QDockWidget("Image viewer", self)
        dock_widget.setWidget(image_viewer)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_widget)

        curve_viewer = CurveViewerWidget(
            sequence_watcher,
            # mot_signal_importer,
            tweezer_importer,
            # average_tweezer_fluo,
            x="start_time",
            y=["survival"],
            # y=["signal"],
        )
        dock_widget = QDockWidget("Curve viewer", self)
        dock_widget.setWidget(curve_viewer)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_widget)
        sequence_watcher.start()
