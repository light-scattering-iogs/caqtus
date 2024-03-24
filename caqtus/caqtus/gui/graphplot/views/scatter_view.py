from __future__ import annotations

import asyncio
from typing import Optional

import attrs
import numpy as np
import polars
import pyqtgraph
import qtawesome
from PySide6.QtCore import QStringListModel
from PySide6.QtWidgets import QWidget, QVBoxLayout, QCompleter

from core.data_analysis.units import extract_unit
from graphplot.views.view import DataView
from .scatter_view_ui import Ui_ScatterView


class ScatterView(DataView, Ui_ScatterView):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setupUi(self)

        self.plot_widget = pyqtgraph.PlotWidget(self, background="white")
        self.plot_widget.enableAutoRange()
        self.plot_item = self.plot_widget.getPlotItem()
        self.scatter_plot = pyqtgraph.ScatterPlotItem()
        self.plot_item.addItem(self.scatter_plot)

        layout = self.layout()
        assert isinstance(layout, QVBoxLayout)
        layout.insertWidget(1, self.plot_widget)
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
        self.scatter_plot.setData([], [])

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
        self.scatter_plot.setData(to_plot.x_values, to_plot.y_values)
        self.plot_item.setLabel("bottom", to_plot.x_label)
        self.plot_item.setLabel("left", to_plot.y_label)

    @staticmethod
    def update_plot(x_column: str, y_column: str, data: polars.DataFrame) -> PlotInfo:
        x_series = data[x_column]
        x_magnitude, x_unit = extract_unit(x_series)
        y_series = data[y_column]
        y_magnitude, y_unit = extract_unit(y_series)

        if x_unit:
            x_label = f"{x_column} [{x_unit:~}]"
        else:
            x_label = x_column
        if y_unit:
            y_label = f"{y_column} [{y_unit:~}]"
        else:
            y_label = y_column

        plot_info = PlotInfo(
            x_values=np.array(x_magnitude),
            y_values=np.array(y_magnitude),
            x_range=(float(x_magnitude.min()), float(x_magnitude.max())),
            y_range=(float(y_magnitude.min()), float(y_magnitude.max())),
            x_label=x_label,
            y_label=y_label,
        )
        return plot_info


@attrs.define
class PlotInfo:
    x_values: np.ndarray
    y_values: np.ndarray
    x_range: tuple[float, float]
    y_range: tuple[float, float]
    x_label: str
    y_label: str
