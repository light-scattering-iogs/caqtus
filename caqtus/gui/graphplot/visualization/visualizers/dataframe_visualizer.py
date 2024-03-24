from __future__ import annotations

from typing import Optional, Any

import polars
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt6.QtWidgets import QTableView
from caqtus.analysis.units import is_quantity_dtype
from caqtus.types.units import Quantity

from ..visualizer_creator import ViewCreator, DataView


class DataFrameViewCreator(ViewCreator):
    def __init__(self) -> None:
        super().__init__()

    def create_view(self) -> DataFrameView:
        return DataFrameView()


class DataFrameView(QTableView, DataView):
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
            column = self._dataframe[column_name]
            value = column[index.row()]
            if is_quantity_dtype(column.dtype):
                quantity = Quantity(value["magnitude"], value["units"])
                return format(quantity, "~")
            else:
                return str(value)

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
