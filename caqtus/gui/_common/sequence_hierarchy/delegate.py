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

from caqtus.session.sequence import State
from caqtus.types.iteration import is_unknown
from caqtus.session.sequence_collection import SequenceStats


class ProgressDelegate(QStyledItemDelegate):
    """Delegate to display the progress of a sequence.

    This custom delegate can be used to display the progress of a sequence in a
    view.
    It should be used for indices that have a :class:`SequenceStats` as their
    display role.
    """

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._progress_bar_option = QStyleOptionProgressBar()
        self._progress_bar_option.textVisible = True
        self._progress_bar_option.minimum = 0

        self._progress_bar_colors = {
            State.DRAFT: None,
            State.PREPARING: None,
            State.RUNNING: None,
            State.INTERRUPTED: QColor(166, 138, 13),
            State.FINISHED: QColor(98, 151, 85),
            State.CRASHED: QColor(240, 82, 79),
        }

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ) -> None:
        sequence_stats = index.data(Qt.ItemDataRole.DisplayRole)
        if isinstance(sequence_stats, SequenceStats):
            self._progress_bar_option.rect = option.rect
            self._progress_bar_option.palette = option.palette

            # Need to choose the color of the text that overlays the progress bar.
            if option.state & QStyle.StateFlag.State_Selected:
                color = option.palette.color(QPalette.ColorRole.HighlightedText)
            else:
                color = option.palette.color(QPalette.ColorRole.Text)
            self._progress_bar_option.palette.setColor(
                QPalette.ColorRole.HighlightedText, color
            )
            progress, maximum = self._get_progress_and_max(sequence_stats)
            self._progress_bar_option.progress = progress
            self._progress_bar_option.maximum = maximum
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
            QApplication.style().drawControl(
                QStyle.ControlElement.CE_ProgressBar, self._progress_bar_option, painter
            )
        else:
            super().paint(painter, option, index)

    @staticmethod
    def _get_text(state: State) -> str:
        return state.value

    def _get_text_color(self, state: State) -> Optional[QColor]:
        return self._get_highlight_color(state)

    def _get_highlight_color(self, state: State) -> Optional[QColor]:
        return self._progress_bar_colors[state]

    @staticmethod
    def _get_progress_and_max(sequence_stats: SequenceStats) -> tuple[int, int]:
        state = sequence_stats.state
        if state == State.DRAFT or state == State.PREPARING:
            progress = 0
            maximum = 100
        else:
            total = sequence_stats.expected_number_shots
            if not is_unknown(total):
                progress = sequence_stats.number_completed_shots
                maximum = total
            else:
                if state == State.RUNNING:  # in progress bar
                    progress = 0
                    maximum = 0
                else:  # filled fixed bar
                    progress = 1
                    maximum = 1
        return progress, maximum
