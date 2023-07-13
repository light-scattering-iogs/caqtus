from typing import Optional, Callable, Any

import numpy
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from experiment.session import (
    ExperimentSessionMaker,
    get_standard_experiment_session_maker,
    ExperimentSession,
)
from sequence.runtime import Shot
from visual.viewer.sequence_viewer import SignalingSequenceWatcher


class ImageViewerCanvas(FigureCanvasQTAgg):
    def __init__(self, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)

        self.image = self.axes.imshow(
            numpy.zeros((100, 100)), origin="lower", cmap="Reds"
        )
        fig.colorbar(self.image, ax=self.axes)

    def set_image(self, image):
        self.image.set_data(image.T)
        self.image.set_clim(vmin=image.min(), vmax=image.T.max())

    def set_title(self, title):
        self.axes.set_title(title)

    def update_plot(self):
        self.draw()


class ImageViewerWidget(QWidget):
    def __init__(
        self,
        sequence_watcher: SignalingSequenceWatcher,
        importer: Callable[[Shot, ExperimentSession], dict[str, Any]],
        image_label: str,
        session_maker: Optional[ExperimentSessionMaker] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent=parent)
        self._sequence_watcher = sequence_watcher
        self._image_viewer_canvas = ImageViewerCanvas()
        self.setLayout(QVBoxLayout())
        navigation_toolbar = NavigationToolbar2QT(self._image_viewer_canvas, self)
        self.layout().addWidget(navigation_toolbar)
        self.layout().addWidget(self._image_viewer_canvas)

        if session_maker is None:
            session_maker = get_standard_experiment_session_maker()
        self._session = session_maker()
        self._sequence_watcher.new_shots_processed.connect(self.on_new_shots_added)
        self._importer = importer
        self._image_label = image_label

    def on_new_shots_added(self, new_shots: list[Shot]):
        with self._session.activate():
            data = self._importer(new_shots[-1], self._session)
        image = data[self._image_label]
        self._image_viewer_canvas.set_image(image)
        self._image_viewer_canvas.set_title(f"Shot {new_shots[-1].index}")
        self._image_viewer_canvas.update_plot()
