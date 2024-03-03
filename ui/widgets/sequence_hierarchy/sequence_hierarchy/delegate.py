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
            if state == State.DRAFT:
                self._progress_bar_option.progress = 0
                self._progress_bar_option.text = "draft"
            elif state == State.PREPARING:
                self._progress_bar_option.progress = 0
                self._progress_bar_option.text = "preparing"
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

                if state == State.RUNNING:
                    self._progress_bar_option.text = "running"
                elif state == State.INTERRUPTED:
                    self._progress_bar_option.text = "interrupted"
                    self._progress_bar_option.palette.setColor(
                        QPalette.ColorRole.Highlight, QColor(166, 138, 13)
                    )
                    self._progress_bar_option.palette.setColor(
                        QPalette.ColorRole.Text, QColor(92, 79, 23)
                    )
                elif state == State.FINISHED:
                    self._progress_bar_option.text = f"finished"
                    self._progress_bar_option.palette.setColor(
                        QPalette.ColorRole.Highlight, QColor(98, 151, 85)
                    )
                    self._progress_bar_option.palette.setColor(
                        QPalette.ColorRole.Text, QColor(255, 255, 255)
                    )
                elif state == State.CRASHED:
                    self._progress_bar_option.text = "crashed"
                    self._progress_bar_option.palette.setColor(
                        QPalette.ColorRole.Text, QColor(119, 46, 44)
                    )
                    self._progress_bar_option.palette.setColor(
                        QPalette.ColorRole.Highlight, QColor(240, 82, 79)
                    )
            QApplication.style().drawControl(
                QStyle.ControlElement.CE_ProgressBar, self._progress_bar_option, painter
            )
        else:
            super().paint(painter, option, index)
