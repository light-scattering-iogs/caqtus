from typing import Optional

from PyQt6.QtCore import QAbstractListModel, QModelIndex, Qt
from PyQt6.QtWidgets import QWidget

from sequence.runtime import Sequence
from .watchlist_widget_ui import Ui_WatchlistWidget
from ..data_loading import DataImporter
from ..sequence_analyzer import SequenceAnalyzer


class WatchlistWidget(QWidget, Ui_WatchlistWidget):
    def __init__(self, sequence_analyzer: SequenceAnalyzer, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._sequence_analyzer_model = SequencesAnalyzerModel(sequence_analyzer)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setupUi(self)
        self._list_view.setModel(self._sequence_analyzer_model)

    def add_sequence(self, sequence: Sequence, data_loader: DataImporter) -> None:
        self._sequence_analyzer_model.add_sequence(sequence, data_loader)


class SequencesAnalyzerModel(QAbstractListModel):
    def __init__(self, sequence_analyzer: SequenceAnalyzer, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._sequence_analyzer = sequence_analyzer
        self._sequences: list[Sequence] = sequence_analyzer.sequences

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._sequence_analyzer.sequences)

    def add_sequence(self, sequence: Sequence, data_loader: DataImporter) -> None:
        # Here we do a full model reset and not just a row insertion, because if the sequence is already
        # in the sequence analyzer, it actually won't be added but just updated.
        self.beginResetModel()
        self._sequence_analyzer.monitor_sequence(sequence, data_loader)
        self.endResetModel()

    def data(
        self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Optional[str]:
        if role == Qt.ItemDataRole.DisplayRole:
            return str(
                list(self._sequence_analyzer.get_sequence_dataframes())[
                    index.row()
                ].path
            )
        return None
