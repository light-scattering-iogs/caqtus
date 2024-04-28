from __future__ import annotations

import asyncio
from typing import Optional, assert_never

import attrs
import pyqtgraph
from PySide6.QtWidgets import QDialog
from PySide6.QtWidgets import QWidget

from caqtus.device import DeviceName
from caqtus.session import Shot, ExperimentSessionMaker
from caqtus.types.data import DataLabel
from caqtus.types.image import ImageLabel, Image
from caqtus.utils import serialization
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
        self.getHistogramWidget().item.sigLevelChangeFinished.connect(
            self._on_levels_changed
        )

    def set_state(self, state: ImageViewState) -> None:
        if state.colormap is not None:
            colormap = pyqtgraph.colormap.get(state.colormap, source="matplotlib")
            self.setColorMap(colormap)
        if state.levels is not None:
            self.setLevels(*state.levels)

    async def display_shot(self, shot: Shot) -> None:
        camera_name = self._state.camera_name
        picture_name = self._state.image
        image = await asyncio.to_thread(
            shot.get_data_by_label, DataLabel(f"{camera_name}\\{picture_name}")
        )
        self.set_image(image)

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


class ImageViewDialog(QDialog, Ui_ImageViewDialog):
    def __init__(self):
        super().__init__()
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
            background=(
                ImageLabel(text)
                if (text := dialog.background_line_edit.text())
                else None
            ),
        )
        return name, serialization.unstructure(state)

    return None
