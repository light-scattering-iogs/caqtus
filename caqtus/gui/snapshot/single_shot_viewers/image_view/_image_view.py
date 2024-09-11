from __future__ import annotations

from typing import Optional, assert_never

import attrs
import numpy as np
import pyqtgraph
from PySide6.QtWidgets import QDialog
from PySide6.QtWidgets import QWidget

from caqtus.device import DeviceName
from caqtus.session import ExperimentSessionMaker
from caqtus.session._data_id import DataId
from caqtus.session._sequence_collection import PureShot
from caqtus.types.data import DataLabel
from caqtus.types.image import ImageLabel, Image, is_image
from caqtus.types.recoverable_exceptions import InvalidTypeError
from caqtus.utils import serialization
from .image_view_dialog_ui import Ui_ImageViewDialog
from ..single_shot_view import ShotView


@attrs.define
class ImageViewState:
    """Contains the state of a view for an image.

    Attributes:
        camera_name: The name of the camera device from which to fetch the image.
        image: The name of the image to fetch.
        background: The name of the background image to fetch.
        colormap: The name of the colormap to use.
        levels: The minimum and maximum values to display.
    """

    camera_name: DeviceName
    image: ImageLabel
    background: Optional[ImageLabel] = None
    colormap: Optional[str] = None
    levels: Optional[tuple[float, float]] = None


class ImageView(ShotView, pyqtgraph.ImageView):
    """A view to display an image for a shot."""

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

    def get_state(self) -> ImageViewState:
        return self._state

    def set_state(self, state: ImageViewState) -> None:
        if state.colormap is not None:
            colormap = pyqtgraph.colormap.get(state.colormap, source="matplotlib")
            self.setColorMap(colormap)
        if state.levels is not None:
            self.setLevels(*state.levels)

    async def display_shot(self, shot: PureShot) -> None:
        image_label = ImageLabel(
            DataLabel(f"{self._state.camera_name}/{self._state.image}")
        )
        background_label = (
            ImageLabel(DataLabel(f"{self._state.camera_name}/{self._state.background}"))
            if self._state.background is not None
            else None
        )

        image = await load_image(
            shot, image_label, background_label, self._session_maker
        )
        self.set_image(image)

    def set_image(self, image: Image) -> None:
        match self._state.levels:
            case None:
                auto_range = True
                levels = None
                auto_histogram_range = True
            case (min_, max_):
                auto_range = False
                auto_histogram_range = False
                levels = (min_, max_)
            case _:
                assert_never(self._state.levels)
        self.setImage(
            image[::, ::-1],
            autoRange=auto_range,
            levels=levels,
            autoHistogramRange=auto_histogram_range,
        )
        self.getHistogramWidget().item.sigLevelsChanged.connect(self._on_levels_changed)

    def _on_levels_changed(self) -> None:
        if self._state.levels is not None:
            self._state.levels = (
                self.getLevels()  # pyright: ignore[reportAttributeAccessIssue]
            )


async def load_image(
    shot: PureShot,
    image_label: ImageLabel,
    background_label: Optional[ImageLabel],
    session_make: ExperimentSessionMaker,
) -> Image[np.floating]:
    async with session_make.async_session() as session:
        image = await session.sequences.get_shot_data_by_label(
            DataId(shot, image_label)
        )
        if not is_image(image):
            raise InvalidTypeError(f"Data {image_label} is not an image.")
        image = image.astype(float)
        if background_label is not None:
            background = await session.sequences.get_shot_data_by_label(
                DataId(shot, background_label)
            )
            if not is_image(background):
                raise InvalidTypeError(f"Data {background_label} is not an image.")
            background = background.astype(float)
            image = image - background
    return image


class ImageViewDialog(QDialog, Ui_ImageViewDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


def create_image_view() -> tuple[str, ImageViewState]:
    dialog = ImageViewDialog()
    result = dialog.exec()
    if result == QDialog.DialogCode.Accepted:
        name = dialog.view_name_line_edit.text()
        state = ImageViewState(
            camera_name=DeviceName(dialog.camera_name_line_edit.text()),
            image=ImageLabel(DataLabel(dialog.image_line_edit.text())),
            background=(
                ImageLabel(DataLabel(text))
                if (text := dialog.background_line_edit.text())
                else None
            ),
        )
        return name, serialization.unstructure(state)

    else:
        raise ValueError("Dialog was cancelled.")
