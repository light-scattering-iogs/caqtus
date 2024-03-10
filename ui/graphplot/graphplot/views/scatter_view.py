import asyncio
from typing import Optional

import matplotlib.style as mplstyle
import polars
import qtawesome
from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.axes import Axes
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from core.data_analysis.units import extract_unit
from graphplot.views.view import DataView
from .scatter_view_ui import Ui_ScatterView

mplstyle.use("fast")


class ScatterView(DataView, Ui_ScatterView):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setupUi(self)
        self.figure = Figure(layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.axis: Axes = self.figure.subplots()  # type: ignore
        layout = self.layout()
        assert isinstance(layout, QVBoxLayout)
        layout.insertWidget(1, self.canvas)
        self.settings_button.setIcon(qtawesome.icon("mdi6.cog"))
        self.apply_button.setIcon(qtawesome.icon("mdi6.check"))
        self.apply_button.clicked.connect(self.on_apply)

        (self.line,) = self.axis.plot([], [], "k.")
        self.clear()

        self.x_column: Optional[str] = None
        self.y_column: Optional[str] = None

    def on_apply(self) -> None:
        x_column = self.x_line_edit.text()
        y_column = self.y_line_edit.text()
        self.x_column = x_column
        self.y_column = y_column

    def clear(self) -> None:
        self.line.set_data([], [])
        self.axis.set_xlabel("$NA$")
        self.axis.set_ylabel("$NA$")
        self.canvas.draw()

    async def update_data(self, data: polars.DataFrame) -> None:
        if self.x_column is None or self.y_column is None:
            self.clear()
            return
        if data.is_empty():
            self.clear()
            return
        await asyncio.to_thread(self.update_plot, self.x_column, self.y_column, data)
        self.canvas.draw()

    def update_plot(self, x_column: str, y_column: str, data: polars.DataFrame) -> None:
        x_series = data[x_column]
        x_magnitude, x_unit = extract_unit(x_series)
        y_series = data[y_column]
        y_magnitude, y_unit = extract_unit(y_series)
        self.line.set_data(x_magnitude, y_magnitude)
        self.axis.relim()
        self.axis.autoscale_view()
        if x_unit:
            self.axis.set_xlabel(f"{x_column} [{x_unit:~}]")
        else:
            self.axis.set_xlabel(x_column)
        if y_unit:
            self.axis.set_ylabel(f"{y_column} [{y_unit:~}]")
        else:
            self.axis.set_ylabel(y_column)

