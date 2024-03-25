from __future__ import annotations

import asyncio
from typing import Optional

import attrs
import numpy as np
import polars
import pyqtgraph
import qtawesome
from PySide6.QtCore import QStringListModel, QTimer, Qt
from PySide6.QtGui import QPen, QFont
from PySide6.QtWidgets import QWidget, QDialog, QCompleter

from caqtus.analysis.stats import compute_stats_average, get_nominal_value, get_error
from caqtus.analysis.units import extract_unit
from caqtus.gui.condetrol._temporary_widget import temporary_widget
from caqtus.gui.graphplot.views.view import DataView
from .error_bar_view_ui import Ui_ErrorBarView
from .settings_dialog_ui import Ui_SettingsDialog


class ErrorBarView(DataView, Ui_ErrorBarView):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.setupUi(self)

        self.settings_button.setIcon(qtawesome.icon("mdi6.cog"))
        self.settings_button.clicked.connect(self.on_settings_button_clicked)

        self.columns_model = QStringListModel(self)

        self.plot: Optional[ErrorBarPlot] = None
        timer = QTimer(self)

    def on_settings_button_clicked(self) -> None:
        with temporary_widget(
            SettingsDialog("View settings...", self.columns_model, self)
        ) as dialog:
            ok = dialog.exec_()
            settings = dialog.get_settings()
        if ok:
            if self.plot is not None:
                self.plot.deleteLater()
            if settings.hue_column is None:
                self.plot = ErrorBarPlot(settings.x_column, settings.y_column, self)
                self.layout().insertWidget(1, self.plot)
            else:
                raise NotImplementedError("Hue column not supported yet.")

    async def update_data(self, data: polars.DataFrame) -> None:
        column_names = data.columns
        if column_names != self.columns_model.stringList():
            # We only reset the completer if the columns have actually changed,
            # otherwise we would reset the user input every time the data is updated.
            self.columns_model.setStringList(data.columns)
        if self.plot is not None:
            await self.plot.update_data(data)


class SettingsDialog(QDialog, Ui_SettingsDialog):
    def __init__(
        self,
        title: str,
        columns_model: QStringListModel,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self.setupUi(self)
        self.setWindowTitle(title)
        self.ok_button.clicked.connect(self.accept)
        self.columns_completer = QCompleter(columns_model, self)
        self.x_line_edit.setCompleter(self.columns_completer)
        self.y_line_edit.setCompleter(self.columns_completer)
        self.hue_line_edit.setCompleter(self.columns_completer)

    def get_settings(self) -> ErrorBarSettings:
        return ErrorBarSettings(
            x_column=self.x_line_edit.text(),
            y_column=self.y_line_edit.text(),
            hue_column=self.hue_line_edit.text() or None,
        )


@attrs.define
class ErrorBarSettings:
    x_column: str
    y_column: str
    hue_column: Optional[str] = None


class ErrorBarPlot(pyqtgraph.PlotWidget):
    def __init__(self, x_column: str, y_column: str, parent: Optional[QWidget] = None):
        super().__init__(parent, background="white")
        black_pen = QPen(Qt.GlobalColor.black)
        self.getAxis("bottom").setTextPen(black_pen)
        self.getAxis("left").setTextPen(black_pen)
        font = QFont()
        font.setPointSize(15)
        self.getAxis("bottom").setTickFont(font)
        self.getAxis("left").setTickFont(font)
        self.getAxis("bottom").label.setFont(font)
        self.getAxis("left").label.setFont(font)
        self.enableAutoRange()

        self.error_bar_item = pyqtgraph.ErrorBarItem()
        self.scatter_plot = pyqtgraph.ScatterPlotItem()
        self.plot_item = self.getPlotItem()
        self.plot_item.addItem(self.error_bar_item)
        self.plot_item.addItem(self.scatter_plot)
        self.x_column = x_column
        self.y_column = y_column

    def clear(self) -> None:
        self.error_bar_item.setData(x=[], y=[], height=[])
        self.plot_item.setLabel("bottom", self.x_column)
        self.plot_item.setLabel("left", self.y_column)

    async def update_data(self, data: polars.DataFrame) -> None:
        if data.is_empty():
            self.clear()
            return
        average = await asyncio.to_thread(
            compute_stats_average, data, [self.y_column], [self.x_column]
        )
        x_magnitudes, x_unit = extract_unit(average[self.x_column])
        y_magnitudes, y_unit = extract_unit(average[self.y_column])
        x = np.array(x_magnitudes)
        y = np.array(get_nominal_value(y_magnitudes))

        self.error_bar_item.setData(
            x=x,
            y=y,
            height=np.array(get_error(y_magnitudes) * 2),
        )
        self.scatter_plot.setData(x=x, y=y)

        if x_unit:
            x_label = f"{self.x_column} [{x_unit:~}]"
        else:
            x_label = self.x_column
        self.plot_item.setLabel("bottom", x_label)

        if y_unit:
            y_label = f"{self.y_column} [{y_unit:~}]"
        else:
            y_label = self.y_column
        self.plot_item.setLabel("left", y_label)
