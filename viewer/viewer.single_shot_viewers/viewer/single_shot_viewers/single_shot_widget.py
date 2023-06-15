from typing import Optional, Iterable, Mapping

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMainWindow,
    QDockWidget,
)

from sequence.runtime import Shot
from .single_shot_viewer import SingleShotViewer


class SingleShotWidget(QMainWindow):
    def __init__(
        self, viewers: Mapping[str, SingleShotViewer], parent: Optional[QWidget] = None
    ):
        super().__init__(parent=parent)
        self._shot_selector = ShotSelector()
        dock_widget = QDockWidget("")
        dock_widget.setWidget(self._shot_selector)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_widget)
        self._viewers = viewers

        self._shot_selector.shot_changed.connect(self._update_viewers)
        for name, viewer in viewers.items():
            dock_widget = QDockWidget(name)
            dock_widget.setWidget(viewer)
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_widget)

    def add_shots(self, shots: Iterable[Shot]) -> None:
        self._shot_selector.add_shots(shots)
        self._update_viewers(self._shot_selector.get_selected_shot())

    def _update_viewers(self, shot) -> None:
        for viewer in self._viewers.values():
            viewer.set_shot(shot)


class ShotSelector(QWidget):
    shot_changed = pyqtSignal(Shot)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent=parent)
        self.setLayout(QHBoxLayout())

        self._shots: list[Shot] = []
        self._label = QLabel()
        self.layout().addWidget(self._label)

        self._current_shot = -1
        self.update_label()

        self._left_button = QPushButton("<")
        self._left_button.setAutoRepeat(True)
        self._left_button.setAutoRepeatInterval(100)
        self._left_button.clicked.connect(self.on_left_button_clicked)
        self.layout().addWidget(self._left_button)

        self._pause_button = QPushButton("||")
        self._pause_button.clicked.connect(self.on_pause_button_clicked)
        self.layout().addWidget(self._pause_button)

        self._right_button = QPushButton(">")
        self._right_button.setAutoRepeat(True)
        self._right_button.setAutoRepeatInterval(100)
        self._right_button.clicked.connect(self.on_right_button_clicked)
        self.layout().addWidget(self._right_button)

        self._last_button = QPushButton(">>")
        self._last_button.clicked.connect(self.on_last_button_clicked)
        self.layout().addWidget(self._last_button)

    def add_shots(self, shots: Iterable[Shot]) -> None:
        self._shots.extend(shots)
        self.update_label()

    def get_selected_shot(self) -> Shot:
        return self._shots[self._current_shot]

    def on_left_button_clicked(self) -> None:
        if self._current_shot == -1:
            self._current_shot = len(self._shots) - 1

        self._current_shot = max(0, self._current_shot - 1)
        self.update_label()
        self.shot_changed.emit(self.get_selected_shot())

    def on_right_button_clicked(self) -> None:
        if self._current_shot == -1:
            self._current_shot = len(self._shots) - 1

        self._current_shot = min(len(self._shots) - 1, self._current_shot + 1)
        self.update_label()
        self.shot_changed.emit(self.get_selected_shot())

    def on_last_button_clicked(self) -> None:
        self._current_shot = -1
        self.update_label()
        self.shot_changed.emit(self.get_selected_shot())

    def on_pause_button_clicked(self) -> None:
        if self._current_shot == -1:
            self._current_shot = len(self._shots) - 1
        self.update_label()
        self.shot_changed.emit(self.get_selected_shot())

    def update_label(self) -> None:
        if self._current_shot == -1:
            current_shot = len(self._shots) - 1
        else:
            current_shot = self._current_shot
        self._label.setText(f"Shot {current_shot + 1}/{len(self._shots)}")
