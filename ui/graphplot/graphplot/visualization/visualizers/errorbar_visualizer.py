from __future__ import annotations

from collections.abc import Sequence
from typing import Optional, Literal, TypeAlias

import numpy as np
import polars
import pyqtgraph
from PyQt6 import QtGui
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget
from pyqtgraph import PlotWidget

from core.data_loading import convert_to_single_unit
from core.types.units import dimensionless, Unit
from .errorbar_visualizer_ui import Ui_ErrorBarVisualizerCreator
from ..visualizer_creator import VisualizerCreator, Visualizer

pyqtgraph.setConfigOptions(antialias=True)


class ErrorBarViewCreator(QWidget, VisualizerCreator, Ui_ErrorBarVisualizerCreator):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setupUi(self)

    def create_visualizer(self) -> ErrorBarView:
        x = self._x_axis_line_edit.text()
        y = self._y_axis_line_edit.text()
        hue = text if (text := self._hue_line_edit.text()) else None
        view = ErrorBarView(x, y, hue)
        font = QtGui.QFont()
        font.setPixelSize(25)
        view.set_axis_tick_font("bottom", font)
        view.set_axis_tick_font("left", font)
        view.set_axis_label_font("bottom", font)
        view.set_axis_label_font("left", font)

        pen = pyqtgraph.mkPen(color=(255, 255, 255), width=2)
        view.set_axis_pen("bottom", pen)
        view.set_axis_pen("left", pen)
        view.getAxis("bottom").setTextPen(pen)
        view.getAxis("left").setTextPen(pen)
        return view


WhichAxis: TypeAlias = Literal["left", "right", "top", "bottom"]


class ErrorBarView(PlotWidget, Visualizer):
    data_updated = pyqtSignal()

    def __init__(self, x: str, y: str, *args, **kwargs):
        PlotWidget.__init__(self, *args, background=(0, 0, 0, 0), **kwargs)

        self._x_var = x
        self._y_var = y
        self._x_unit: Optional[Unit] = None
        self._y_unit: Optional[Unit] = None

        self._x_values = np.array([])
        self._y_values = np.array([])
        self._error_values = np.array([])

        self._error_bar_plotter = FilledErrorBarPlotter()

        self._setup_ui()

    def _setup_ui(self):
        for item in self._error_bar_plotter.get_items():
            self.addItem(item)
        self.update_plot()
        self.data_updated.connect(self.update_plot)  # type:ignore

    def set_axis_tick_font(self, axis: WhichAxis, font: QtGui.QFont) -> None:
        self.getAxis(axis).setStyle(tickFont=font)

    def set_axis_label_font(self, axis: WhichAxis, font: QtGui.QFont) -> None:
        self.getAxis(axis).label.setFont(font)

    def set_axis_pen(self, axis: WhichAxis, pen: pyqtgraph.mkPen) -> None:
        self.plotItem.getAxis(axis).setPen(pen)

    def update_plot(self):
        self.update_axis_labels()
        self._error_bar_plotter.set_data(
            x=self._x_values,
            y=self._y_values,
            error=self._error_values,
        )

    def update_axis_labels(self):
        self.setLabel("left", format_label(self._y_var, self._y_unit))
        self.setLabel("bottom", format_label(self._x_var, self._x_unit))

    def update_data(self, dataframe: Optional[polars.DataFrame]) -> None:
        if dataframe is not None and len(dataframe) > 0:
            self.process_data(dataframe)
        else:
            self._x_values = np.array([])
            self._y_values = np.array([])
            self._error_values = np.array([])

        # We don't want to update the plot directly here because if this is not running in the same thread the plot
        # items leave in, that would lead to a crash. Instead, we emit the signal and do the plot update in the slot.
        self.data_updated.emit()  # type: ignore

    def process_data(self, dataframe: polars.DataFrame) -> None:
        x_var = self._x_var
        y_var = self._y_var

        x_magnitudes, self._x_unit = convert_to_single_unit(dataframe[x_var])
        y_magnitudes, self._y_unit = convert_to_single_unit(dataframe[y_var])

        data = polars.DataFrame([x_magnitudes, y_magnitudes])

        mean = polars.col(y_var).mean()
        sem = polars.col(y_var).std() / polars.Expr.sqrt(polars.col(y_var).count())
        stats = (
            data.lazy()
            .group_by(x_var)
            .agg(mean.alias(f"{y_var}.mean"), sem.alias(f"{y_var}.sem"))
            .sort(by=x_var)
            .collect()
        )

        self._x_values = stats[x_var].to_numpy()
        self._y_values = stats[f"{y_var}.mean"].to_numpy()
        self._error_values = stats[f"{y_var}.sem"].to_numpy()

    def plot_with_hue(self, dataframe: polars.DataFrame) -> None:
        x_var = self._x_var
        y_var = self._y_var
        hue = self.hue
        mean = polars.col(y_var).mean()
        sem = polars.col(y_var).std() / polars.Expr.sqrt(polars.col(y_var).count())
        stats = (
            dataframe.lazy()
            .group_by(x_var, hue)
            .agg(mean.alias(f"{y_var}.mean"), sem.alias(f"{y_var}.sem"))
            .sort(hue, x_var)
            .collect()
        )
        for hue_value, group in stats.group_by(hue, maintain_order=True):
            self.plot_curve(
                group[x_var].to_numpy(),
                group[f"{y_var}.mean"].to_numpy(),
                group[f"{y_var}.sem"].to_numpy(),
                label=hue_value,
            )
        self._axis.legend(title=hue)


def format_label(label: str, unit: Optional[Unit]) -> str:
    if unit is None:
        return label
    else:
        if unit == dimensionless:
            return label
        else:
            return f"{label} [{unit:~}]"


class ErrorBarPlotter:
    def __init__(self):
        self._error_bar_item = pyqtgraph.ErrorBarItem(
            x=np.array([]), y=np.array([]), height=np.array([])
        )

    def set_data(self, x, y, error) -> None:
        self._error_bar_item.setData(x=x, y=y, height=error)

    def get_items(self) -> Sequence[pyqtgraph.GraphicsObject]:
        return [self._error_bar_item]


class FilledErrorBarPlotter:
    def __init__(self):
        self._top_curve = pyqtgraph.PlotCurveItem(x=np.array([]), y=np.array([]))
        self._bottom_curve = pyqtgraph.PlotCurveItem(x=np.array([]), y=np.array([]))
        self._middle_curve = pyqtgraph.PlotCurveItem(
            x=np.array([], dtype=float), y=np.array([], dtype=float),
            pen=pyqtgraph.mkPen("w", width=2)
        )
        self._fill = pyqtgraph.FillBetweenItem(
            self._top_curve, self._bottom_curve, brush=0.2
        )

    def set_data(self, x, y, error) -> None:
        # Here 1.96 refers to the 95% confidence interval
        self._top_curve.setData(x, y + error * 1.96)
        self._bottom_curve.setData(x, y - error * 1.96)
        self._middle_curve.setData(x, y)

    def get_items(self) -> Sequence[pyqtgraph.GraphicsObject]:
        return [self._fill, self._middle_curve]
