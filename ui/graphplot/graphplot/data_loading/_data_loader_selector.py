from typing import Mapping

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget

from ._data_importer import DataImporter
from .data_loader_selector_ui import Ui_DataLoaderSelector


class DataLoaderSelector(QWidget, Ui_DataLoaderSelector):
    # This signal emit an object of type DataImporter. However, this is not a real type, which is an issue for Qt, so we
    # put object instead of DataImporter here.
    data_loader_selected = pyqtSignal(object)

    def __init__(
        self, data_loaders: Mapping[str, DataImporter], *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)

        self._data_loaders = dict(data_loaders)

        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setupUi(self)
        for data_loader in self._data_loaders:
            self._data_loader_combo_box.addItem(data_loader)
        self._apply_button.clicked.connect(self._on_apply_button_clicked)

    def _on_apply_button_clicked(self) -> None:
        data_loader_name = self._data_loader_combo_box.currentText()
        data_loader = self._data_loaders[data_loader_name]

        self.data_loader_selected.emit(data_loader)  # type: ignore
