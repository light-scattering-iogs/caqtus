import threading
from typing import Optional

import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from analyza.loading.importers import ShotImporter
from experiment.session import ExperimentSession, get_standard_experiment_session
from image_types import Image
from sequence.runtime import Shot
from .single_shot_viewer import SingleShotViewer


class ImageViewer(SingleShotViewer):
    def __init__(
        self,
        *,
        importer: ShotImporter[Image],
        session: Optional[ExperimentSession] = None,
        parent: Optional[QWidget] = None,
        vmin: Optional[float] = None,
        vmax: Optional[float] = None,
        cmap: Optional[str] = None,
    ):
        super().__init__(parent=parent)

        if session is None:
            session = get_standard_experiment_session()

        self._importer = importer
        self._session = session
        self._image = None

        self._lock = threading.Lock()

        self._cmap = cmap
        self._vmin: Optional[float] = vmin
        self._vmax: Optional[float] = vmax

        self._setup_ui()

    def _setup_ui(self) -> None:
        self._figure = Figure()
        self._axes = self._figure.add_subplot()
        self._canvas = FigureCanvasQTAgg(self._figure)
        self._colorbar = None

        self._setup_image(np.full((10, 10), np.nan))

        self.setLayout(QVBoxLayout())
        navigation_toolbar = NavigationToolbar2QT(self._canvas, self)
        self.layout().addWidget(navigation_toolbar)
        self.layout().addWidget(self._canvas)

    def _setup_image(self, image: Image) -> None:
        if self._colorbar is not None:
            self._colorbar.remove()
        self._axes.clear()
        self._image = self._axes.imshow(
            image.T, origin="lower", cmap=self._cmap, vmin=self._vmin, vmax=self._vmax
        )
        self._colorbar = self._figure.colorbar(self._image, ax=self._axes)

    def set_shot(self, shot: Shot) -> None:
        with self._lock, self._session.activate():
            try:
                image = self._importer(shot, self._session)
            except Exception as e:
                self._set_exception(e)
            else:
                self._set_image(image)

    def update_view(self) -> None:
        self._canvas.draw()

    def _set_image(self, image: Image) -> None:
        if image.shape != self._image.get_array().shape:
            self._setup_image(image)
        self._image.set_data(image.T)
        if self._vmin is None:
            vmin = np.min(image)
        else:
            vmin = self._vmin
        if self._vmax is None:
            vmax = np.max(image)
        else:
            vmax = self._vmax
        self._image.set_clim(vmin=vmin, vmax=vmax)

    def _set_exception(self, error: Exception):
        self._axes.clear()
        self._axes.text(
            0.5,
            0.5,
            f"{error!r}",
            horizontalalignment="center",
            verticalalignment="center",
            color="red",
        )
        self._canvas.draw()
