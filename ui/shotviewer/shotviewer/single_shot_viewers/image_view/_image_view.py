from __future__ import annotations

import queue
from typing import Optional, assert_never

import attrs
import numpy as np
import pyqtgraph
from PySide6.QtCore import QThread, Signal, QTimer
from PySide6.QtWidgets import QDialog
from PySide6.QtWidgets import QWidget
from core.device import DeviceName
from core.session import Shot, ExperimentSessionMaker
from core.types.image import ImageLabel, Image
from util import serialization

from .image_view_dialog_ui import Ui_ImageViewDialog
from ..single_shot_view import ShotView


@attrs.define
class ImageViewState:
    camera_name: DeviceName
    image: ImageLabel
    background: Optional[ImageLabel] = None
    colormap: Optional[str] = None
    levels: Optional[tuple[float, float]] = None


class ImageView(ShotView, pyqtgraph.ImageView):
    def __init__(
        self,
        state: ImageViewState,
        session_maker: ExperimentSessionMaker,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._state = state
        self.set_state(state)
        self._session_maker = session_maker
        self._shot_queue = queue.Queue[Shot]()
        self._fetch_image_thread = self._FetchImageThread(
            session_maker, self._shot_queue, parent=self
        )
        self._fetch_image_thread.image_loaded.connect(self.set_image)  # type: ignore
        self.destroyed.connect(self._fetch_image_thread.quit)
        self.getHistogramWidget().item.sigLevelChangeFinished.connect(
            self._on_levels_changed
        )
        self._fetch_image_thread.start()

    def set_state(self, state: ImageViewState) -> None:
        if state.colormap is not None:
            colormap = pyqtgraph.colormap.get(state.colormap, source="matplotlib")
            self.setColorMap(colormap)
        if state.levels is not None:
            self.setLevels(*state.levels)

    def display_shot(self, shot: Shot) -> None:
        self._shot_queue.put(shot)

    def set_image(self, image: Image) -> None:
        match self._state.levels:
            case None:
                autoRange = True
                levels = None
                autoHistogramRange = True
            case (min_, max_):
                autoRange = False
                autoHistogramRange = False
                levels = (min_, max_)
            case _:
                assert_never(self._state.levels)
        self.setImage(
            image[::, ::-1],
            autoRange=autoRange,
            levels=levels,
            autoHistogramRange=autoHistogramRange,
        )
        self.getHistogramWidget().item.sigLevelsChanged.connect(self._on_levels_changed)

    def _on_levels_changed(self) -> None:
        if self._state.levels is not None:
            self._state.levels = self.getLevels()

    class _FetchImageThread(QThread):
        image_loaded = Signal(np.ndarray)

        def __init__(
            self,
            session_maker: ExperimentSessionMaker,
            shot_queue: queue.Queue[Shot],
            parent: ImageView,
        ):
            super().__init__(parent=parent)
            self._parent = parent
            self._session_maker = session_maker
            self._shot_queue = shot_queue
            self._timer = QTimer()
            self._timer.moveToThread(self)

        def run(self):
            self._timer.singleShot(30, self.fetch)
            self.exec()

        def fetch(self):
            try:
                shot = self._shot_queue.get(block=False)
            except queue.Empty:
                pass
            else:
                while not self._shot_queue.empty():
                    shot = self._shot_queue.get()
                with self._session_maker() as session:
                    camera_name = self._parent._state.camera_name
                    picture_name = self._parent._state.image
                    image = shot.get_data_by_label(
                        f"{camera_name}\\{picture_name}", session
                    )
                    self.image_loaded.emit(image)  # type: ignore
            self._timer.singleShot(30, self.fetch)


class ImageViewDialog(QDialog, Ui_ImageViewDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent=parent)
        self.setupUi(self)


def create_image_view(
    parent: Optional[QWidget] = None,
) -> Optional[tuple[str, ImageViewState]]:
    dialog = ImageViewDialog(parent=parent)
    result = dialog.exec()
    if result == QDialog.DialogCode.Accepted:
        name = dialog.view_name_line_edit.text()
        state = ImageViewState(
            camera_name=DeviceName(dialog.camera_name_line_edit.text()),
            image=ImageLabel(dialog.image_line_edit.text()),
            background=ImageLabel(text)
            if (text := dialog.background_line_edit.text())
            else None,
        )
        return name, serialization.unstructure(state)

    return None
