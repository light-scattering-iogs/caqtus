import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QDockWidget

from analyza.import_data import (
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


def get_atom_detector() -> AtomDetector:
    session = get_standard_experiment_session()
    with session.activate():
        detector_config = session.get_current_experiment_config().get_device_config(
            "Atom detector"
        )
        return AtomDetector(
            name="detector", **detector_config.get_device_init_args("5x5 tweezers")
        )


detector = get_atom_detector()


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
    image = data["Orca Quest.picture"]  # - data["Orca Quest.background"]

    signals = detector.compute_signals(image)
    d = {f"signal_{trap}": s for trap, s in signals.items()}
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
        super().__init__()
        sequence_watcher = SignalingSequenceWatcher(
            sequence=Sequence("2023.05_May.24.lifetime_3"),
            importer=tweezer_importer,
            # importer=image_importer("picture"),
            watch_interval=0.1,
            chunk_size=20,
        )

        image_viewer = ImageViewerWidget(
            sequence_watcher, importer=image_importer("picture"), image_label="image"
        )
        dock_widget = QDockWidget("Image viewer", self)
        dock_widget.setWidget(image_viewer)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_widget)

        image_viewer = ImageViewerWidget(
            sequence_watcher, importer=image_importer("picture 3"), image_label="image"
        )
        dock_widget = QDockWidget("Image viewer", self)
        dock_widget.setWidget(image_viewer)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_widget)

        curve_viewer = CurveViewerWidget(
            sequence_watcher,
            # mot_signal_importer,
            tweezer_importer,
            # average_tweezer_fluo,
            x="start_time",
            y=[f"signal_{trap}" for trap in sorted(detector.get_traps_labels())],
            # y=["signal"],
        )
        dock_widget = QDockWidget("Curve viewer", self)
        dock_widget.setWidget(curve_viewer)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_widget)
        sequence_watcher.start()
