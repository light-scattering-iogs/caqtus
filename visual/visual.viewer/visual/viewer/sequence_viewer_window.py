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
from atom_detector import WeightedAtomSignalCalculator
from sequence.runtime import Sequence
from settings_model import YAMLSerializable
from .curve_plotter import CurveViewerWidget
from .image_viewer import ImageViewerWidget
from .sequence_viewer import SignalingSequenceWatcher

traps_file = (
    "C:\\Users\\Elizabeth\\Dropbox\\Dy\\Scripts\\2023\\03_March\\31\\traps.yaml"
)
with open(traps_file) as file:
    traps: list[WeightedAtomSignalCalculator] = YAMLSerializable.load(file)


def importer(shot, session):
    parameters = (import_parameters | break_namespaces | split_units)(
        shot, session
    ) | import_time(shot, session)
    data = (import_measures | array_as_float)(shot, session)
    image = data["Orca Quest.picture"] - 0 * data["Orca Quest.background"]
    signal = traps[1].compute_signal(image)
    return {**parameters, "signal": signal}


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
    image = data["Orca Quest.picture"] - data["Orca Quest.background"]

    signal = traps[3].compute_signal(image)
    return {**parameters, "signal": signal}


def image_importer(shot, session):
    data = (import_measures | array_as_float)(shot, session)
    image = data["Orca Quest.picture"] - data["Orca Quest.background"]
    return {"image": image}


class SequenceViewerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        sequence_watcher = SignalingSequenceWatcher(
            sequence=Sequence("2023.03_March.31.imaging_frequency_and_power_highB_1"),
            importer=importer,
            watch_interval=0.3,
            chunk_size=20,
        )

        image_viewer = ImageViewerWidget(sequence_watcher, importer=image_importer, image_label="image")
        dock_widget = QDockWidget("Image viewer", self)
        dock_widget.setWidget(image_viewer)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_widget)

        curve_viewer = CurveViewerWidget(
            sequence_watcher,
            tweezer_importer,
            x="start_time",
            y="signal",
        )
        dock_widget = QDockWidget("Curve viewer", self)
        dock_widget.setWidget(curve_viewer)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_widget)
        sequence_watcher.start()
