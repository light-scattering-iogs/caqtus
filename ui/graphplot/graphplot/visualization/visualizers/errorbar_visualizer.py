from __future__ import annotations

from typing import Optional

import numpy as np
import pandas
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

    def update_data(self, dataframe: Optional[pandas.DataFrame]) -> None:
        self._axis.clear()
        self._axis.set_ylabel(self._y)
        self._axis.set_xlabel(self._x)
        if dataframe is not None:
            long = pandas.wide_to_long(
                dataframe.reset_index(),
                ["picture 1", "picture 2"],
                i=["sequence", "shot"],
                j="atom",
            )

            def survival(row):
                if row["picture 1"] == 1:
                    return row["picture 2"]
                else:
                    return np.nan

            long["survival"] = long.apply(survival, axis=1)
            self.plot_data(long)

        self._canvas.draw()

    def plot_data(self, dataframe: pandas.DataFrame) -> None:
        if self.hue:
            for sequence, hue_group in dataframe.groupby(self.hue):
                variable_group = hue_group.groupby(self._x)
                average = variable_group[self._y].mean()
                error = variable_group[self._y].sem()
                self._axis.errorbar(
                    average.index, average, error, fmt="o", label=sequence
                )
            self._axis.legend(title=self.hue)
        else:
            variable_group = dataframe.groupby(self._x)
            average = variable_group[self._y].mean()
            error = variable_group[self._y].sem()
            self._axis.errorbar(average.index, average, error, fmt="o")
