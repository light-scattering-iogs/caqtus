from typing import Optional

from PySide6.QtCore import QModelIndex, Qt
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
    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ) -> None:
        model = index.model()
        sequence_stats: Optional[SequenceStats] = model.data(index, Qt.ItemDataRole.DisplayRole)
        if sequence_stats:
            opt = QStyleOptionProgressBar()
            opt.rect = option.rect
            opt.minimum = 0
            opt.maximum = 100
            opt.textVisible = True
            state = sequence_stats.state
            if state == State.DRAFT:
                opt.progress = 0
                opt.text = "draft"
            elif state == State.PREPARING:
                opt.progress = 0
                opt.text = "preparing"
            else:
                total = sequence_stats.expected_number_shots
                if total:
                    opt.progress = sequence_stats.number_completed_shots
                    opt.maximum = total
                else:
                    if state == State.RUNNING:  # filled bar with sliding reflects
                        opt.progress = 0
                        opt.maximum = 0
                    else:  # filled bar
                        opt.progress = 1
                        opt.maximum = 1

                if state == State.RUNNING:
                    opt.text = "running"
                elif state == State.INTERRUPTED:
                    opt.text = "interrupted"
                    opt.palette.setColor(
                        QPalette.ColorRole.Highlight, QColor(166, 138, 13)
                    )
                    opt.palette.setColor(QPalette.ColorRole.Text, QColor(92, 79, 23))
                elif state == State.FINISHED:
                    opt.text = f"finished"
                    opt.palette.setColor(
                        QPalette.ColorRole.Highlight, QColor(98, 151, 85)
                    )
                    opt.palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
                elif state == State.CRASHED:
                    opt.text = "crashed"
                    opt.palette.setColor(QPalette.ColorRole.Text, QColor(119, 46, 44))
                    opt.palette.setColor(
                        QPalette.ColorRole.Highlight, QColor(240, 82, 79)
                    )
            QApplication.style().drawControl(
                QStyle.ControlElement.CE_ProgressBar, opt, painter
            )
        else:
            super().paint(painter, option, index)
