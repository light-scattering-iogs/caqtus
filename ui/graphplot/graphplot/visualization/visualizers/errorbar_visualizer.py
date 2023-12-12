from __future__ import annotations

from collections.abc import Sequence
from typing import Optional, Literal, TypeAlias, Any

import attrs
import numpy as np
import polars
import pyqtgraph
from PyQt6 import QtGui, QtCore
from PyQt6.QtWidgets import QWidget
from core.data_analysis.stats import compute_stats_average
from core.data_analysis.units import extract_unit
from core.types.units import dimensionless, Unit
from pyqtgraph import PlotWidget

from .errorbar_visualizer_ui import Ui_ErrorBarVisualizerCreator
from ..visualizer_creator import ViewCreator, DataView

pyqtgraph.setConfigOptions(antialias=True)


class ErrorBarViewCreator(QWidget, ViewCreator, Ui_ErrorBarVisualizerCreator):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setupUi(self)

    def create_view(self) -> ErrorBarView:
        x = self._x_axis_line_edit.text()
        y = self._y_axis_line_edit.text()
        hue = text if (text := self._hue_line_edit.text()) else None
        if hue is None:
            view = ErrorBarView(x, y)
        else:
            view = HueErrorBarView(x, y, hue)
        font = QtGui.QFont()
        font.setPixelSize(25)
        view.getAxis("bottom").setStyle(tickFont=font)
        view.getAxis("left").setStyle(tickFont=font)
        view.getAxis("bottom").label.setFont(font)
        view.getAxis("left").label.setFont(font)

        pen = pyqtgraph.mkPen(color=(255, 255, 255), width=2)
        view.plotItem.getAxis("bottom").setPen(pen)
        view.plotItem.getAxis("left").setPen(pen)
        view.getAxis("bottom").setTextPen(pen)
        view.getAxis("left").setTextPen(pen)
        return view


WhichAxis: TypeAlias = Literal["left", "right", "top", "bottom"]


@attrs.define
class Stats:
    x_values: np.ndarray
    y_values: np.ndarray
    error_values: np.ndarray
    x_unit: Optional[Unit]
    y_unit: Optional[Unit]


class HueErrorBarView(PlotWidget, DataView):
    def __init__(self, x: str, y: str, hue: str, *args, **kwargs):
        PlotWidget.__init__(self, *args, background=(0, 0, 0, 0), **kwargs)

        self._x_var = x
        self._y_var = y
        self._hue = hue

        self._stats: Optional[polars.DataFrame] = None

        self._error_bar_plotters: dict[Any, FilledErrorBarPlotter] = {}
        self._compute_stats_thread: Optional[ComputeStatsThread] = None

        self.update_plot()

    def update_plot(self) -> None:
        stats = self._stats
        if stats is None or len(stats) == 0:
            x_unit = None
            y_unit = None
            hue_unit = None
        else:
            for hue, group in stats.groupby(self._hue):
                if hue not in self._error_bar_plotters:
                    self._error_bar_plotters[hue] = FilledErrorBarPlotter()
                    for item in self._error_bar_plotters[hue].get_items():
                        self.addItem(item)
                x_series, x_unit = extract_unit(group[self._x_var])
                y_series, y_unit = extract_unit(group[f"{self._y_var}.mean"])
                error_series, _ = extract_unit(group[f"{self._y_var}.sem"])
                x_values = np.array(x_series.to_numpy())
                y_values = np.array(y_series.to_numpy())
                error_values = np.array(error_series.to_numpy())
                self._error_bar_plotters[hue].set_data(
                    x=x_values,
                    y=y_values,
                    error=error_values,
                )

        self.update_axis_labels(x_unit, y_unit)

    def update_axis_labels(
        self, x_unit: Optional[Unit], y_unit: Optional[Unit]
    ) -> None:
        self.setLabel("bottom", format_label(self._x_var, x_unit))
        self.setLabel("left", format_label(self._y_var, y_unit))

    def update_data(self, dataframe: Optional[polars.DataFrame]) -> None:
        if self._compute_stats_thread is not None:
            if self._compute_stats_thread.isRunning():
                return
        self._compute_stats_thread = ComputeStatsThread(
            self, dataframe, self._x_var, self._y_var, hue=self._hue
        )
        self._compute_stats_thread.finished.connect(self.update_plot)  # type: ignore
        self._compute_stats_thread.start()


class ErrorBarView(PlotWidget, DataView):
    def __init__(self, x: str, y: str, *args, **kwargs):
        PlotWidget.__init__(self, *args, background=(0, 0, 0, 0), **kwargs)

        self._x_var = x
        self._y_var = y

        self._stats: Optional[polars.DataFrame] = None

        self._error_bar_plotter = FilledErrorBarPlotter()
        self._compute_stats_thread: Optional[ComputeStatsThread] = None

        self._setup_ui()

    def _setup_ui(self):
        for item in self._error_bar_plotter.get_items():
            self.addItem(item)
        self.update_plot()

    def update_plot(self) -> None:
        stats = self._stats
        if stats is None:
            x_unit = None
            y_unit = None
            x_values = np.array([])
            y_values = np.array([])
            error_values = np.array([])
        else:
            x_series, x_unit = extract_unit(stats[self._x_var])
            y_series, y_unit = extract_unit(stats[f"{self._y_var}.mean"])
            error_series, _ = extract_unit(stats[f"{self._y_var}.sem"])
            x_values = x_series.to_numpy()
            y_values = y_series.to_numpy()
            error_values = error_series.to_numpy()

        self.update_axis_labels(x_unit, y_unit)
        self._error_bar_plotter.set_data(
            x=x_values,
            y=y_values,
            error=error_values,
        )

    def update_axis_labels(
        self, x_unit: Optional[Unit], y_unit: Optional[Unit]
    ) -> None:
        self.setLabel("bottom", format_label(self._x_var, x_unit))
        self.setLabel("left", format_label(self._y_var, y_unit))

    def update_data(self, dataframe: Optional[polars.DataFrame]) -> None:
        if self._compute_stats_thread is not None:
            if self._compute_stats_thread.isRunning():
                return
        self._compute_stats_thread = ComputeStatsThread(
            self,
            dataframe,
            self._x_var,
            self._y_var,
        )
        self._compute_stats_thread.finished.connect(self.update_plot)  # type: ignore
        self._compute_stats_thread.start()


class ComputeStatsThread(QtCore.QThread):
    def __init__(
        self,
        parent: ErrorBarView,
        dataframe: Optional[polars.DataFrame],
        x_var: str,
        y_var: str,
        hue: Optional[str] = None,
    ):
        super().__init__(parent=parent)
        self._parent = parent
        self._dataframe = dataframe
        self._x_var = x_var
        self._y_var = y_var
        self._hue = hue

    def run(self) -> None:
        if self._dataframe is not None and len(self._dataframe) > 0:
            group_by = [self._x_var] if self._hue is None else [self._hue, self._x_var]
            self._parent._stats = compute_stats_average(
                self._dataframe, self._y_var, group_by
            )
        else:
            self._parent.stats = None


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
            x=np.array([], dtype=float),
            y=np.array([], dtype=float),
            pen=pyqtgraph.mkPen("w", width=2),
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
