from typing import Mapping

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout

from util.itertools import first
from .visualizer_creator import Visualizer, VisualizerCreator
from .visualizer_creators_selector_ui import Ui_VisualizerCreatorSelector


class VisualizerCreatorSelector(QWidget, Ui_VisualizerCreatorSelector):
    visualizer_selected = pyqtSignal(Visualizer)

    def __init__(
        self, visualizer_creators: Mapping[str, VisualizerCreator], *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)

        self._visualizer_creators = dict(visualizer_creators)
        self._current_visualizer_creator: VisualizerCreator = first(
            visualizer_creators.values()
        )
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setupUi(self)
        for visualiser_creator in self._visualizer_creators:
            self._visualizer_combo_box.addItem(visualiser_creator)
        self._apply_button.clicked.connect(self._on_apply_button_clicked)
        self._settings_group.setHidden(True)
        self._visualizer_combo_box.currentTextChanged.connect(
            self._on_visualizer_creator_selected
        )
        self._settings_group.setLayout(QVBoxLayout())

    def _on_visualizer_creator_selected(self, visualizer_creator_name: str) -> None:
        self._current_visualizer_creator = self._visualizer_creators[
            visualizer_creator_name
        ]
        layout = self._settings_group.layout()
        while layout.count() > 0:
            layout.itemAt(0).widget().setParent(None)
        if isinstance(self._current_visualizer_creator, QWidget):
            self._settings_group.layout().addWidget(self._current_visualizer_creator)
            self._settings_group.setHidden(False)
        else:
            self._settings_group.setHidden(True)

    def _on_apply_button_clicked(self) -> None:
        self.visualizer_selected.emit(self._current_visualizer_creator.create_visualizer())  # type: ignore
