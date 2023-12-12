from typing import Optional

from PyQt6 import QtGui
from PyQt6.QtCore import QAbstractListModel, QModelIndex, Qt
from PyQt6.QtWidgets import QWidget
from core.session.sequence import Sequence

from .watchlist_widget_ui import Ui_WatchlistWidget
from ..data_loading import DataImporter
from ..sequence_analyzer import SequenceAnalyzer


class WatchlistWidget(QWidget, Ui_WatchlistWidget):
    def __init__(self, sequence_analyzer: SequenceAnalyzer, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._sequence_analyzer_model = WatchlistModel(sequence_analyzer)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setupUi(self)
        self._list_view.setModel(self._sequence_analyzer_model)

    def add_sequence(self, sequence: Sequence, data_loader: DataImporter) -> None:
        self._sequence_analyzer_model.add_sequence(sequence, data_loader)

    def keyPressEvent(self, a0: Optional[QtGui.QKeyEvent]) -> None:
        if (a0 is not None) and a0.key() == Qt.Key.Key_Delete:
            self._remove_selected_sequences()
        super().keyPressEvent(a0)

    def _remove_selected_sequences(self) -> None:
        selected_indexes = self._list_view.selectedIndexes()
        # We sort the indexes in reverse order to avoid index shifting when removing rows
        sorted_indexes = sorted(
            selected_indexes, key=lambda index: index.row(), reverse=True
        )
        for index in sorted_indexes:
            self._sequence_analyzer_model.removeRow(index.row())


class WatchlistModel(QAbstractListModel):
    def __init__(self, sequence_analyzer: SequenceAnalyzer, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._sequence_analyzer = sequence_analyzer
        self._sequences: list[Sequence] = sequence_analyzer.sequences

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._sequences)

    def add_sequence(self, sequence: Sequence, data_loader: DataImporter) -> None:
        # Here we do a full model reset and not just a row insertion, because if the sequence is already
        # in the sequence analyzer, it actually won't be added but just updated.
        self.beginResetModel()
        self._sequence_analyzer.monitor_sequence(sequence, data_loader)
        self._sequences = self._sequence_analyzer.sequences
        self.endResetModel()

    def data(
        self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Optional[str]:
        if role == Qt.ItemDataRole.DisplayRole:
            return str(self._sequences[index.row()].path)
        return None

    def removeRow(self, row: int, parent: QModelIndex = QModelIndex()) -> bool:
        """Removes a sequence from the watchlist."""

        sequence_to_stop_watching = self._sequences[row]
        self.beginRemoveRows(parent, row, row)
        self._sequence_analyzer.stop_monitoring_sequence(sequence_to_stop_watching)
        self._sequences.pop(row)
        self.endRemoveRows()
        return True
