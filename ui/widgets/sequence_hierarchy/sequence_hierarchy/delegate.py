from typing import Optional

from PySide6.QtCore import QModelIndex, Qt, QObject
from PySide6.QtGui import (
    QColor,
    QPalette,
    QPainter,
)
from PySide6.QtWidgets import (
    QStyleOptionViewItem,
    QStyleOptionProgressBar,
    QApplication,
    QStyle,
    QStyledItemDelegate,
)

from core.session.sequence import State
from core.session.sequence_collection import SequenceStats


class ProgressDelegate(QStyledItemDelegate):
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._progress_bar_option = QStyleOptionProgressBar()
        self._progress_bar_option.textVisible = True
        self._progress_bar_option.minimum = 0

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ) -> None:
        sequence_stats = index.data(Qt.ItemDataRole.DisplayRole)
        assert sequence_stats is None or isinstance(sequence_stats, SequenceStats)
        if sequence_stats:
            self._progress_bar_option.rect = option.rect
            self._progress_bar_option.palette = option.palette
            self._progress_bar_option.maximum = 100
            state = sequence_stats.state
            self._progress_bar_option.text = self._get_text(state)
            text_color = self._get_text_color(state)
            if text_color is not None:
                self._progress_bar_option.palette.setColor(
                    QPalette.ColorRole.Text, text_color
                )
            highlight_color = self._get_highlight_color(state)
            if highlight_color is not None:
                self._progress_bar_option.palette.setColor(
                    QPalette.ColorRole.Highlight, highlight_color
                )
            if state == State.DRAFT:
                self._progress_bar_option.progress = 0
            elif state == State.PREPARING:
                self._progress_bar_option.progress = 0
            else:
                total = sequence_stats.expected_number_shots
                if total is not None:
                    self._progress_bar_option.progress = (
                        sequence_stats.number_completed_shots
                    )
                    self._progress_bar_option.maximum = total
                else:
                    if state == State.RUNNING:  # filled bar with sliding reflects
                        self._progress_bar_option.progress = 0
                        self._progress_bar_option.maximum = 0
                    else:  # filled bar
                        self._progress_bar_option.progress = 1
                        self._progress_bar_option.maximum = 1
            QApplication.style().drawControl(
                QStyle.ControlElement.CE_ProgressBar, self._progress_bar_option, painter
            )
        else:
            super().paint(painter, option, index)

    @staticmethod
    def _get_text(state: State) -> str:
        result = {
            State.DRAFT: "draft",
            State.PREPARING: "preparing",
            State.RUNNING: "running",
            State.INTERRUPTED: "interrupted",
            State.FINISHED: "finished",
            State.CRASHED: "crashed",
        }
        return result[state]

    @staticmethod
    def _get_text_color(state: State) -> Optional[QColor]:
        result = {
            State.DRAFT: None,
            State.PREPARING: None,
            State.RUNNING: None,
            State.INTERRUPTED: QColor(92, 79, 23),
            State.FINISHED: QColor(255, 255, 255),
            State.CRASHED: QColor(119, 46, 44),
        }
        return result[state]

    @staticmethod
    def _get_highlight_color(state: State) -> Optional[QColor]:
        result = {
            State.DRAFT: None,
            State.PREPARING: None,
            State.RUNNING: None,
            State.INTERRUPTED: QColor(166, 138, 13),
            State.FINISHED: QColor(98, 151, 85),
            State.CRASHED: QColor(240, 82, 79),
        }
        return result[state]

