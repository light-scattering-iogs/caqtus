import numpy
import pandas
from PyQt6.QtCharts import QLineSeries, QChart, QChartView, QValueAxis
from PyQt6.QtCore import pyqtSignal, QObject, Qt
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QDockWidget

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
        self,
        sequence: Sequence,
        session_maker: ExperimentSessionMaker,
        importer,
        update_interval: float = 1,
    ):
        super().__init__(sequence, session_maker, importer, update_interval)
        QObject.__init__(self)

    def process_shot(self, shot: Shot):
        if shot.index > 0:
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
        roi = (slice(50, 150), slice(50, 180))
        importer = (
            import_all
            | break_namespaces
            | split_units
            | array_as_float
            # | apply(lambda image: numpy.sum(image[roi]-201) * 0.11, "Orca Quest.picture", "fluo")
            | apply(lambda image, background: numpy.mean(image-background), ["MOT camera.picture", "MOT camera.background"], "fluo")
        )
        sequence_watcher = SignalingSequenceWatcher(
            sequence,
            self._session_maker,
            importer,
            update_interval=0.5
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
