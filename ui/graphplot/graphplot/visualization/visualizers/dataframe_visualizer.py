from __future__ import annotations

from typing import Optional, Any

import polars
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt6.QtWidgets import QTableView

from ..visualizer_creator import VisualizerCreator, Visualizer


class DataFrameVisualizerCreator(VisualizerCreator):
    def __init__(self) -> None:
        super().__init__()

    def create_visualizer(self) -> DataFrameVisualizer:
        return DataFrameVisualizer()


class DataFrameVisualizer(QTableView, Visualizer):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._model = DataFrameModel(polars.DataFrame())
        self.setModel(self._model)

    def update_data(self, dataframe: Optional[polars.DataFrame]) -> None:
        if dataframe is None:
            dataframe = polars.DataFrame()
        self._model.update_dataframe(dataframe)


class DataFrameModel(QAbstractTableModel):
    def __init__(self, dataframe: polars.DataFrame, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._dataframe = dataframe

    def update_dataframe(self, dataframe: polars.DataFrame) -> None:
        self.beginResetModel()
        self._dataframe = dataframe
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._dataframe)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._dataframe.columns)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            column_name = self._dataframe.columns[index.column()]
            return str(self._dataframe[column_name][index.row()])

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self._dataframe.columns[section]
            elif orientation == Qt.Orientation.Vertical:
                return section
