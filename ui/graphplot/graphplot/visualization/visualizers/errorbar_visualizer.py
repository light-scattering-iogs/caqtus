from __future__ import annotations

from typing import Optional

import polars
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from .errorbar_visualizer_ui import Ui_ErrorBarVisualizerCreator
from ..visualizer_creator import VisualizerCreator, Visualizer


class ErrorBarVisualizerCreator(
    QWidget, VisualizerCreator, Ui_ErrorBarVisualizerCreator
):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setupUi(self)

    def create_visualizer(self) -> ErrorbarVisualizer:
        x = self._x_axis_line_edit.text()
        y = self._y_axis_line_edit.text()
        hue = text if (text := self._hue_line_edit.text()) else None
        return ErrorbarVisualizer(x, y, hue)


class ErrorbarVisualizer(Visualizer):
    def __init__(self, x: str, y: str, hue: Optional[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._x = x
        self._y = y
        self.hue = hue
        self._setup_ui()

    def _setup_ui(self) -> None:
        self._figure = Figure()
        self._axis = self._figure.add_subplot()
        self._canvas = FigureCanvasQTAgg(self._figure)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self._canvas)

    def update_data(self, dataframe: Optional[polars.DataFrame]) -> None:
        self._axis.clear()
        self._axis.set_ylabel(self._y)
        self._axis.set_xlabel(self._x)
        if dataframe is not None:
            self.plot_data(dataframe)
        self._canvas.draw()

    def plot_data(self, dataframe: polars.DataFrame) -> None:
        x_var = self._x
        y_var = self._y
        mean = polars.col(y_var).mean()
        sem = polars.col(y_var).std() / polars.Expr.sqrt(polars.col(y_var).count())
        stats = (
            dataframe.lazy()
            .group_by(x_var)
            .agg(mean.alias(f"{y_var}.mean"), sem.alias(f"{y_var}.sem"))
            .sort(by=x_var)
            .collect()
        )
        self._axis.errorbar(
            stats[x_var].to_numpy(),
            stats[f"{y_var}.mean"].to_numpy(),
            stats[f"{y_var}.sem"].to_numpy(),
            fmt="o",
        )
