from typing import Optional

import seaborn
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from sequence.runtime import Shot
from visual.viewer.sequence_viewer import SignalingSequenceWatcher


class CurveViewerCanvas(FigureCanvasQTAgg):
    def __init__(self, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)


class CurveViewerWidget(QWidget):
    def __init__(
        self,
        sequence_watcher: SignalingSequenceWatcher,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent=parent)
        self._sequence_watcher = sequence_watcher
        self._curve_viewer_canvas = CurveViewerCanvas()
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self._curve_viewer_canvas)

        self._sequence_watcher.new_shots_processed.connect(self.on_new_shots_added)

    def on_new_shots_added(self, new_shots: list[Shot]):
        data = self._sequence_watcher.get_current_dataframe()
        self._curve_viewer_canvas.axes.clear()
        seaborn.lineplot(data, x="start_time", y="signal", ax=self._curve_viewer_canvas.axes)
        self._curve_viewer_canvas.draw()

