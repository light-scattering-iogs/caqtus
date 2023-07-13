from typing import Optional, Callable, Any, Iterable

import numpy
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from experiment.session import (
    ExperimentSession,
)
from experiment.session import (
    ExperimentSessionMaker,
    get_standard_experiment_session_maker,
)
from sequence.runtime import Shot
from visual.viewer.sequence_viewer import SignalingSequenceWatcher


class CurveViewerCanvas(FigureCanvasQTAgg):
    def __init__(self, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)

        (self.line,) = self.axes.plot(
            [],
            [],
            "o",
            color="black",
            markersize=2,
            markerfacecolor="black",
            markeredgecolor="black",
            markeredgewidth=0.5,
        )

    def add_point(self, x, y):
        self.line.set_xdata(numpy.append(self.line.get_xdata(), x))
        self.line.set_ydata(numpy.append(self.line.get_ydata(), y))

    def add_points(self, x, y):
        self.line.set_xdata(numpy.concatenate((self.line.get_xdata(), x)))
        self.line.set_ydata(numpy.concatenate((self.line.get_ydata(), y)))

    def set_title(self, title):
        self.axes.set_title(title)

    def rescale(self):
        self.axes.relim()
        self.axes.autoscale_view()

    def update_plot(self):
        self.draw()


class CurveViewerWidget(QWidget):
    def __init__(
        self,
        sequence_watcher: SignalingSequenceWatcher,
        importer: Callable[[Shot, ExperimentSession], dict[str, Any]],
        x: str,
        y: Iterable[str],
        session_maker: Optional[ExperimentSessionMaker] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent=parent)
        self._sequence_watcher = sequence_watcher
        self._curve_viewer_canvas = CurveViewerCanvas()
        self._importer = importer
        self._x = x
        self._y = y
        self.setLayout(QVBoxLayout())
        navigation_toolbar = NavigationToolbar2QT(self._curve_viewer_canvas, self)
        self.layout().addWidget(navigation_toolbar)
        self.layout().addWidget(self._curve_viewer_canvas)

        if session_maker is None:
            session_maker = get_standard_experiment_session_maker()
        self._session = session_maker()
        self._sequence_watcher.new_shots_processed.connect(self.on_new_shots_added)

    def on_new_shots_added(self, new_shots: list[Shot]):
        x = []
        y = []
        with self._session.activate():
            for shot in new_shots:
                data = self._importer(shot, self._session)
                y_values = [data[y_key] for y_key in self._y]
                y += y_values
                x += [shot.index] * len(y_values)
        self._curve_viewer_canvas.add_points(x, y)
        self._curve_viewer_canvas.set_title(f"Shot {new_shots[-1].index}")
        self._curve_viewer_canvas.rescale()
        self._curve_viewer_canvas.update_plot()
