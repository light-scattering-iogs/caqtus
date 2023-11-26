from __future__ import annotations

from collections.abc import Sequence
from typing import Optional, Literal, TypeAlias

import attrs
import numpy as np
import polars
import pyqtgraph
from PyQt6 import QtGui, QtCore
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget
from pyqtgraph import PlotWidget

from core.data_loading import convert_to_single_unit
from core.types.units import dimensionless, Unit
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


@attrs.define
class Stats:
    x_values: np.ndarray
    y_values: np.ndarray
    error_values: np.ndarray
    x_unit: Optional[Unit]
    y_unit: Optional[Unit]


class ComputeStatsThread(QtCore.QThread):
    stats_computed = pyqtSignal(Stats)

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
            stats = self.process_data()
        else:
            stats = Stats(
                x_values=np.array([]),
                y_values=np.array([]),
                error_values=np.array([]),
                x_unit=None,
                y_unit=None,
            )
        self._parent._stats = stats

    def process_data(self) -> Stats:
        x_var = self._x_var
        y_var = self._y_var

        x_magnitudes, x_unit = convert_to_single_unit(self._dataframe[x_var])
        y_magnitudes, y_unit = convert_to_single_unit(self._dataframe[y_var])

        data = polars.DataFrame([x_magnitudes, y_magnitudes])

        mean = polars.col(y_var).mean()
        sem = polars.col(y_var).std() / polars.Expr.sqrt(polars.col(y_var).count())
        dataframe_stats = (
            data.lazy()
            .group_by(x_var)
            .agg(mean.alias(f"{y_var}.mean"), sem.alias(f"{y_var}.sem"))
            .sort(by=x_var)
            .collect()
        )

        stats = Stats(
            x_values=dataframe_stats[x_var].to_numpy(),
            y_values=dataframe_stats[f"{y_var}.mean"].to_numpy(),
            error_values=dataframe_stats[f"{y_var}.sem"].to_numpy(),
            x_unit=x_unit,
            y_unit=y_unit,
        )
        return stats


class ErrorBarView(PlotWidget, DataView):
    def __init__(self, x: str, y: str, *args, **kwargs):
        PlotWidget.__init__(self, *args, background=(0, 0, 0, 0), **kwargs)

        self._x_var = x
        self._y_var = y

        self._stats = Stats(
            x_values=np.array([]),
            y_values=np.array([]),
            error_values=np.array([]),
            x_unit=None,
            y_unit=None,
        )

        self._error_bar_plotter = FilledErrorBarPlotter()
        self._compute_stats_thread: Optional[ComputeStatsThread] = None

        self._setup_ui()

    def _setup_ui(self):
        for item in self._error_bar_plotter.get_items():
            self.addItem(item)
        stats = Stats(
            x_values=np.array([]),
            y_values=np.array([]),
            error_values=np.array([]),
            x_unit=None,
            y_unit=None,
        )
        self.update_plot()

    def set_axis_tick_font(self, axis: WhichAxis, font: QtGui.QFont) -> None:
        self.getAxis(axis).setStyle(tickFont=font)

    def set_axis_label_font(self, axis: WhichAxis, font: QtGui.QFont) -> None:
        self.getAxis(axis).label.setFont(font)

    def set_axis_pen(self, axis: WhichAxis, pen: pyqtgraph.mkPen) -> None:
        self.plotItem.getAxis(axis).setPen(pen)

    def update_plot(self) -> None:
        stats = self._stats
        self.update_axis_labels(stats)
        self._error_bar_plotter.set_data(
            x=stats.x_values,
            y=stats.y_values,
            error=stats.error_values,
        )

    def update_axis_labels(self, stats: Stats):
        self.setLabel("left", format_label(self._y_var, stats.y_unit))
        self.setLabel("bottom", format_label(self._x_var, stats.x_unit))

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
