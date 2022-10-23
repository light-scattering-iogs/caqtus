import logging
from pathlib import Path

from PyQt5.QtCore import Qt, QModelIndex
from PyQt5.QtWidgets import QWidget, QTableView, QVBoxLayout, QSizePolicy, QSplitter

from .swim_lane_model import SwimLaneModel

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ShotWidget(QWidget):
    def __init__(self, sequence_path: Path, *args):
        super().__init__(*args)
        self._sequence_path = sequence_path
        self.model = SwimLaneModel(self._sequence_path, "shot")

        self.layout = QVBoxLayout()
        self.layout.addWidget(SwimLaneWidget(self.model))
        self.setLayout(self.layout)


class SpanTableView(QTableView):
    def __init__(self):
        super().__init__()

    def update_span(self):
        for row in range(self.model().rowCount()):
            for column in range(self.model().columnCount()):
                index = self.model().index(row, column, QModelIndex())
                span = self.model().span(index)
                self.setSpan(row, column, span.height(), span.width())


class SwimLaneWidget(QWidget):
    def __init__(self, model: SwimLaneModel, *args):
        super().__init__(*args)

        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Vertical)
        self.setLayout(QVBoxLayout())

        self._model = model

        self.steps_view = QTableView()
        self.steps_view.setModel(self._model)
        for i in range(2, self._model.rowCount()):
            self.steps_view.setRowHidden(i, True)

        self.steps_view.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.steps_view.setAlternatingRowColors(True)
        policy = self.steps_view.sizePolicy()
        policy.setVerticalPolicy(QSizePolicy.Policy.Fixed)
        self.steps_view.setSizePolicy(policy)
        self.update_section_height()
        self.steps_view.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.steps_view.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.lanes_view = SpanTableView()
        self.lanes_view.setModel(self._model)
        self.lanes_view.horizontalHeader().hide()
        self.lanes_view.setRowHidden(0, True)
        self.lanes_view.setRowHidden(1, True)

        policy = self.lanes_view.sizePolicy()
        policy.setVerticalPolicy(QSizePolicy.Policy.MinimumExpanding)
        self.lanes_view.setSizePolicy(policy)
        self.lanes_view.setMinimumHeight(0)

        splitter.addWidget(self.steps_view)
        splitter.addWidget(self.lanes_view)

        self.layout().addWidget(splitter)

        self.update_vertical_header_width()
        self.steps_view.horizontalHeader().sectionResized.connect(
            self.update_section_width
        )
        self.steps_view.verticalHeader().sectionResized.connect(
            self.update_section_height
        )
        self.lanes_view.horizontalScrollBar().valueChanged.connect(
            self.steps_view.horizontalScrollBar().setValue
        )
        self.lanes_view.update_span()

    def update_vertical_header_width(self):
        new_width = max(
            self.lanes_view.verticalHeader().width(),
            self.steps_view.verticalHeader().width(),
        )
        self.lanes_view.verticalHeader().setFixedWidth(new_width)
        self.steps_view.verticalHeader().setFixedWidth(new_width)

    def update_section_width(self, logicalIndex: int, oldSize: int, newSize: int):
        self.lanes_view.setColumnWidth(logicalIndex, newSize)

    def update_section_height(self, *args):
        height = (
            self.steps_view.horizontalHeader().height()
            + self.steps_view.rowHeight(0)
            + self.steps_view.rowHeight(1)
            + 5
        )
        self.steps_view.setFixedHeight(height)
