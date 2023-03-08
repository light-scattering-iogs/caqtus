from datetime import datetime

import numpy
import pandas
from PyQt6.QtCharts import QLineSeries, QChart, QChartView, QValueAxis
from PyQt6.QtCore import pyqtSignal, QObject, QDateTime, Qt
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QDockWidget, QVBoxLayout

from analyza import (
    import_all,
    split_units,
    array_as_float,
    break_namespaces,
    apply,
    DataframeSequenceWatcher,
)
from experiment.session import ExperimentSessionMaker
from sequence.runtime import Sequence, Shot


class SignalingSequenceWatcher(DataframeSequenceWatcher, QObject):
    new_shot_processed = pyqtSignal(pandas.Index)
    sequence_reset = pyqtSignal()

    def __init__(
        self, sequence: Sequence, session_maker: ExperimentSessionMaker, importer
    ):
        super().__init__(sequence, session_maker, importer)
        QObject.__init__(self)

    def process_shot(self, shot: Shot):
        index = super().process_shot(shot)
        # noinspection PyUnresolvedReferences
        self.new_shot_processed.emit(index)

    def reset(self):
        super().reset()
        # noinspection PyUnresolvedReferences
        self.sequence_reset.emit()


class SequenceViewer(QDockWidget):
    def __init__(self, sequence: Sequence, session_maker: ExperimentSessionMaker):
        super().__init__()
        self._session_maker = session_maker
        self._sequence = sequence

        self._series = QLineSeries()
        self._chart = QChart()
        self._chart.legend().hide()
        self.axis_x = QValueAxis()
        self.axis_y = QValueAxis()
        self._chart.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)
        self._chart.addAxis(self.axis_y, Qt.AlignmentFlag.AlignLeft)
        self._chart.addSeries(self._series)
        self._series.attachAxis(self.axis_x)
        self._series.attachAxis(self.axis_y)

        self._chart_view = QChartView(self._chart)
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)

        self.setWidget(self._chart_view)

        self._sequence_watcher = self._create_sequence_watcher(sequence)
        self._sequence_watcher.start()
        # noinspection PyUnresolvedReferences
        self._sequence_watcher.new_shot_processed.connect(self._on_new_shot_processed)

    def _create_sequence_watcher(self, sequence: Sequence):
        importer = (
            import_all
            | break_namespaces
            | split_units
            | array_as_float
            | apply(lambda image: numpy.mean(image), "MOT camera.picture", "fluo")
        )
        sequence_watcher = SignalingSequenceWatcher(
            sequence, self._session_maker, importer
        )
        return sequence_watcher

    def _on_new_shot_processed(self, index: pandas.Index):
        data = self._sequence_watcher.get_dataframe()
        y_data = data["fluo"][index]
        for x, y in zip(index, y_data):
            self._series.append(x[2], y)

        # self.axis_x.setRange(data["s"], max(mapping.output_values))
        x_min = data.index.get_level_values("index").min()
        x_max = data.index.get_level_values("index").max()
        self.axis_x.setRange(x_min, x_max)
        self.axis_y.setRange(data["fluo"].min(), data["fluo"].max())
