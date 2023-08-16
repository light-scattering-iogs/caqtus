import threading
from typing import Optional

import numpy as np
from PyQt6.QtWidgets import QVBoxLayout
from attr import field
from attrs import define
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

import serialization
from analyza.loading.importers import ImageImporter
from experiment.session import ExperimentSession, get_standard_experiment_session
from image_types import Image
from sequence.runtime import Shot
from .single_shot_viewer import SingleShotViewer


@define
class ImageViewerConfiguration:
    vmin: Optional[float] = None
    vmax: Optional[float] = None
    cmap: Optional[str] = "viridis"


@serialization.customize(
    _importer=serialization.override(rename="importer"),
    _vmin=serialization.override(rename="vmin"),
    _vmax=serialization.override(rename="vmax"),
    _cmap=serialization.override(rename="cmap"),
)
@define(slots=False, init=False)
class ImageViewer(SingleShotViewer):
    _importer: ImageImporter = field(default=None)

    _vmin: Optional[float] = field(default=None)
    _vmax: Optional[float] = field(default=None)
    _cmap: Optional[str] = field(default="viridis")

    def __init__(
        self,
        importer: ImageImporter,
        vmin: Optional[float] = None,
        vmax: Optional[float] = None,
        cmap: Optional[str] = "viridis",
        session: Optional[ExperimentSession] = None,
    ):
        super().__init__()

        self.__attrs_init__(importer=importer, vmin=vmin, vmax=vmax, cmap=cmap)

        self._lock = threading.Lock()
        self._image = None
        self._figure = None
        self._axes = None
        self._canvas = None
        self._colorbar = None
        if session is None:
            session = get_standard_experiment_session()
        self._session = session

        self._setup_ui()

    @property
    def cmap(self) -> Optional[str]:
        return self._cmap

    @cmap.setter
    def cmap(self, cmap: Optional[str]) -> None:
        self._cmap = cmap
        self._image.set_cmap(cmap)
        self.update_view()

    @property
    def vmin(self) -> Optional[float]:
        return self._vmin

    @vmin.setter
    def vmin(self, vmin: Optional[float]) -> None:
        self._vmin = vmin
        self._image.set_clim(vmin=vmin)
        self.update_view()

    @property
    def vmax(self) -> Optional[float]:
        return self._vmax

    @vmax.setter
    def vmax(self, vmax: Optional[float]) -> None:
        self._vmax = vmax
        self._image.set_clim(vmax=vmax)
        self.update_view()

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

    def _setup_image(self, image: Image):
        if self._colorbar is not None:
            self._colorbar.remove()
        self._axes.clear()
        self._image = self._axes.imshow(
            image.T, origin="lower", cmap=self.cmap, vmin=self.vmin, vmax=self.vmax
        )
        self._colorbar = self._figure.colorbar(self._image, ax=self._axes)
        return image

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
        if self.vmin is None:
            vmin = np.min(image)
        else:
            vmin = self.vmin
        if self.vmax is None:
            vmax = np.max(image)
        else:
            vmax = self.vmax
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
