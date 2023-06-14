from typing import Optional, Collection, Iterable

from PyQt6.QtWidgets import QWidget, QVBoxLayout

from sequence.runtime import Shot
from .single_shot_viewer import SingleShotViewer


class SingleShotWidget(QWidget):
    def __init__(
        self, viewers: Collection[SingleShotViewer], parent: Optional[QWidget] = None
    ):
        super().__init__(parent=parent)
        self.setLayout(QVBoxLayout())
        self._viewers = viewers
        for viewer in viewers:
            self.layout().addWidget(viewer)

        self._shots: list[Shot] = []

    def add_shots(self, shots: Iterable[Shot]) -> None:
        self._shots.extend(shots)
        current_shot = self._shots[-1]
        for viewer in self._viewers:
            viewer.set_shot(current_shot)
