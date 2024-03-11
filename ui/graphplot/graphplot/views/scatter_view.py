from __future__ import annotations

import asyncio
from typing import Optional

import attrs
import matplotlib.style as mplstyle
import polars
import qtawesome
from PySide6.QtCharts import QChartView, QScatterSeries, QValueAxis, QChart
from PySide6.QtCore import QStringListModel, QPointF, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QCompleter

from core.data_analysis.units import extract_unit
from graphplot.views.view import DataView
from .scatter_view_ui import Ui_ScatterView

mplstyle.use("fast")


class ScatterView(DataView, Ui_ScatterView):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setupUi(self)
        self.chart_view = QChartView(self)
        self.series = QScatterSeries(self.chart_view)

        self.series.setMarkerSize(5)
        self.series.setUseOpenGL(True)
        self.chart_view.chart().setTheme(QChart.ChartTheme.ChartThemeLight)
        self.series.setMarkerShape(QScatterSeries.MarkerShape.MarkerShapePentagon)
        self.chart_view.chart().legend().hide()

        self.chart_view.chart().addSeries(self.series)
        self.x_axis = QValueAxis(self)
        self.y_axis = QValueAxis(self)
        self.chart_view.chart().addAxis(self.x_axis, Qt.AlignmentFlag.AlignBottom)
        self.chart_view.chart().addAxis(self.y_axis, Qt.AlignmentFlag.AlignLeft)
        self.series.attachAxis(self.x_axis)
        self.series.attachAxis(self.y_axis)

        layout = self.layout()
        assert isinstance(layout, QVBoxLayout)
        layout.insertWidget(1, self.chart_view)
        self.settings_button.setIcon(qtawesome.icon("mdi6.cog"))
        self.apply_button.setIcon(qtawesome.icon("mdi6.check"))
        self.apply_button.clicked.connect(self.on_apply)

        self.clear()

        self.x_column: Optional[str] = None
        self.y_column: Optional[str] = None

        self.columns_model = QStringListModel(self)
        self.columns_completer = QCompleter(self.columns_model, self)
        self.x_line_edit.setCompleter(self.columns_completer)
        self.y_line_edit.setCompleter(self.columns_completer)

    def on_apply(self) -> None:
        x_column = self.x_line_edit.text()
        y_column = self.y_line_edit.text()
        self.x_column = x_column
        self.y_column = y_column

    def clear(self) -> None:
        self.series.clear()
        self.chart_view.update()

    async def update_data(self, data: polars.DataFrame) -> None:
        column_names = data.columns
        if column_names != self.columns_model.stringList():
            # We only reset the completer if the columns have actually changed,
            # otherwise we would reset the user input.
            self.columns_model.setStringList(data.columns)
        if self.x_column is None or self.y_column is None:
            self.clear()
            return
        if data.is_empty():
            self.clear()
            return
        to_plot = await asyncio.to_thread(
            self.update_plot, self.x_column, self.y_column, data
        )
        self.series.replace(to_plot.points)
        self.x_axis.setRange(*to_plot.x_range)
        self.y_axis.setRange(*to_plot.y_range)

    @staticmethod
    def update_plot(
            x_column: str, y_column: str, data: polars.DataFrame
    ) -> PlotInfo:
        x_series = data[x_column]
        x_magnitude, x_unit = extract_unit(x_series)
        y_series = data[y_column]
        y_magnitude, y_unit = extract_unit(y_series)
        new_points = [QPointF(x, y) for x, y in zip(x_magnitude, y_magnitude)]
        plot_info = PlotInfo(
            points=new_points,
            x_range=(float(x_magnitude.min()), float(x_magnitude.max())),
            y_range=(float(y_magnitude.min()), float(y_magnitude.max())),
        )

        # self.line.set_data(x_magnitude, y_magnitude)
        # self.axis.relim()
        # self.axis.autoscale_view()
        # if x_unit:
        #     self.axis.set_xlabel(f"{x_column} [{x_unit:~}]")
        # else:
        #     self.axis.set_xlabel(x_column)
        # if y_unit:
        #     self.axis.set_ylabel(f"{y_column} [{y_unit:~}]")
        # else:
        #     self.axis.set_ylabel(y_column)
        return plot_info


@attrs.define
class PlotInfo:
    points: list[QPointF]
    x_range: tuple[float, float]
    y_range: tuple[float, float]
