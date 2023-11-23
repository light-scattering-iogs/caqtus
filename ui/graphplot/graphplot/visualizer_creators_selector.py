from typing import Mapping

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget

from .visualizer_creator import Visualizer, VisualizerCreator
from .visualizer_creators_selector_ui import Ui_VisualizerCreatorSelector


class VisualizerCreatorSelector(QWidget, Ui_VisualizerCreatorSelector):
    visualizer_selected = pyqtSignal(Visualizer)

    def __init__(
        self, visualizer_creators: Mapping[str, VisualizerCreator], *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)

        self._visualizer_creators = dict(visualizer_creators)

        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setupUi(self)
        for visualiser_creator in self._visualizer_creators:
            self._visualizer_combo_box.addItem(visualiser_creator)
        self._apply_button.clicked.connect(self._on_apply_button_clicked)

    def _on_apply_button_clicked(self) -> None:
        visualizer_creator_name = self._visualizer_combo_box.currentText()
        visualizer_creator = self._visualizer_creators[visualizer_creator_name]

        self.visualizer_selected.emit(visualizer_creator.create_visualizer())  # type: ignore
