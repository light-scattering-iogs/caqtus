from __future__ import annotations

import asyncio
from typing import Optional

import numpy as np
import polars
import pyqtgraph
import qtawesome
from PySide6.QtCore import QStringListModel
from PySide6.QtWidgets import QWidget, QVBoxLayout, QCompleter

from core.data_analysis.units import extract_unit
from graphplot.views.view import DataView
from .error_bar_view_ui import Ui_ErrorBarView


class ErrorBarView(DataView, Ui_ErrorBarView):
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

    async def update_data(self, data: polars.DataFrame) -> None:
        pass


class ErrorBarPlot(pyqtgraph.PlotWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent, background="white")
        self.enableAutoRange()

        self.plot_item = self.plot_widget.getPlotItem()
        self.error_bar_item = pyqtgraph.ErrorBarItem()
        self.plot_item.addItem(self.error_bar_item)
