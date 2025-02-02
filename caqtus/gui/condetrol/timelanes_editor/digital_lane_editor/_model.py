from typing import Optional, Any, assert_never

from PySide6.QtCore import QObject, QModelIndex, Qt, QPersistentModelIndex
from PySide6.QtGui import QAction, QBrush, QPalette
from PySide6.QtWidgets import QMenu

from caqtus.types.expression import Expression
from caqtus.types.timelane import DigitalTimeLane
from .._colored_time_lane_model import ColoredTimeLaneModel

_DEFAULT_INDEX = QModelIndex()


class DigitalTimeLaneModel(ColoredTimeLaneModel[DigitalTimeLane]):
    # ruff: noqa: N802
    def __init__(self, name: str, parent: Optional[QObject] = None):
        lane = DigitalTimeLane([False])
        super().__init__(name, lane, parent)
        if self._brush is None:
            # If no brush is set the button will be invisible, so we pick the
            # base color from the palette as default.
            color = QPalette().text().color()
            self._brush = QBrush(color)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        value = self.lane_value(index.row())
        if role == Qt.ItemDataRole.DisplayRole:
            if isinstance(value, bool):
                return
            elif isinstance(value, Expression):
                return str(value)
            else:
                assert_never(value)
        elif role == Qt.ItemDataRole.EditRole:
            return value
        elif role == Qt.ItemDataRole.BackgroundRole:
            if isinstance(value, bool):
                if value:
                    return self._brush
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter
        else:
            return super().data(index, role)

    def setData(self, index, value: Any, role: int = Qt.ItemDataRole.EditRole):
        if not index.isValid():
            return False
        if role == Qt.ItemDataRole.EditRole:
            assert isinstance(value, bool | Expression)
            return self.set_lane_value(index.row(), value)
        return False

    def insertRow(
        self, row, parent: QModelIndex | QPersistentModelIndex = _DEFAULT_INDEX
    ) -> bool:
        return self.insert_lane_value(row, False)

    def get_cell_context_actions(self, index: QModelIndex) -> list[QAction | QMenu]:
        if not index.isValid():
            return []
        cell_type_menu = QMenu("Cell type")
        value = self.lane_value(index.row())
        bool_action = cell_type_menu.addAction("on/off")
        if isinstance(value, bool):
            bool_action.setCheckable(True)
            bool_action.setChecked(True)
        else:
            bool_action.triggered.connect(
                lambda: self.setData(index, False, Qt.ItemDataRole.EditRole)
            )
        expr_action = cell_type_menu.addAction("expression")
        if isinstance(value, Expression):
            expr_action.setCheckable(True)
            expr_action.setChecked(True)
        else:
            expr_action.triggered.connect(
                lambda: self.setData(index, Expression("..."), Qt.ItemDataRole.EditRole)
            )

        return super().get_cell_context_actions(index) + [cell_type_menu]
