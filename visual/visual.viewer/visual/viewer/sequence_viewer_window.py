from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow

from analyza.import_data import (
    import_all,
    break_namespaces,
    split_units,
    array_as_float,
    remove,
)
from sequence.runtime import Sequence
from .image_viewer import ImageViewerWidget
from .sequence_viewer import SignalingSequenceWatcher


class SequenceViewerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        sequence_watcher = SignalingSequenceWatcher(
            sequence=Sequence("2023.03_March.29.hist_vs_exposure"),
            importer=(
                import_all
                | break_namespaces
                | split_units
                | array_as_float
                | remove("clear", "Orca Quest.first_picture", "Orca Quest.picture")
                # # | apply(lambda image: numpy.sum(image[roi]-201) * 0.11, "Orca Quest.picture", "fluo")
                # | apply(
                #     lambda image, background: numpy.sum(image[roi] - background[roi]),
                #     ["MOT camera.picture", "MOT camera.background"],
                #     "fluo",
                # )
            ),
            watch_interval=0.3,
        )

        image_viewer = ImageViewerWidget(sequence_watcher)

        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, image_viewer)
        sequence_watcher.start()
