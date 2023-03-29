from typing import Optional

import numpy
from PyQt6.QtWidgets import QDockWidget, QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure, Axes

from experiment.session import (
    ExperimentSessionMaker,
    get_standard_experiment_session_maker,
)
from sequence.runtime import Shot
from visual.viewer.sequence_viewer import SignalingSequenceWatcher


class ImageViewerWidget(QDockWidget, FigureCanvasQTAgg):
    def __init__(
        self,
        sequence_watcher: SignalingSequenceWatcher,
        session_maker: Optional[ExperimentSessionMaker] = None,
        parent: Optional[QWidget] = None,
        width=5,
        height=4,
        dpi=100,
    ):
        QDockWidget.__init__(self, parent=parent)
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes: Axes = fig.add_subplot(111)
        FigureCanvasQTAgg.__init__(self, fig)
        self._sequence_watcher = sequence_watcher
        self.image = self.axes.imshow(
            numpy.zeros((100, 100)), origin="lower", cmap="Reds"
        )
        if session_maker is None:
            session_maker = get_standard_experiment_session_maker()
        self._session = session_maker()
        self._sequence_watcher.new_shots_processed.connect(self.on_new_shots_added)

    def on_new_shots_added(self, new_shots: list[Shot]):
        with self._session.activate():
            data = new_shots[-1].get_measures(self._session)
        image = data["Orca Quest"]["picture"].astype(float) - data["Orca Quest"][
            "background"
        ].astype(float)
        self.image.set_data(image.T)
        self.image.set_clim(vmin=0, vmax=image.max())
        self.axes.set_title(f"Shot {new_shots[-1].index}")
        self.draw()
