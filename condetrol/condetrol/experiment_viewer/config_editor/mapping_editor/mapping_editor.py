from PyQt6.QtCharts import QChartView, QLineSeries, QChart, QValueAxis
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QHBoxLayout, QDialog

from device_config.units_mapping import CalibratedUnitsMapping


class CalibratedMappingEditor(QDialog):
    """Widget to edit the calibrated mapping of a channel

    This widget contains an editable list of measured data points and a view of the
    interpolation between the points.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setSizeGripEnabled(True)
        self.setWindowTitle("Edit unit mapping...")
        self.resize(400, 300)

        self.layout = QHBoxLayout()
        self.series = QLineSeries()

        self.axis_x = QValueAxis()
        self.axis_y = QValueAxis()

        self.chart = QChart()
        self.chart.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignmentFlag.AlignLeft)
        self.chart.legend().hide()
        self.chart.setTitle("Unit interpolation")

        self.chart.addSeries(self.series)

        self.series.attachAxis(self.axis_x)
        self.series.attachAxis(self.axis_y)
        self.series.setPointsVisible(True)

        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.layout.addWidget(self.chart_view)
        self.setLayout(self.layout)

    def set_unit_mapping(self, mapping: CalibratedUnitsMapping):
        self.series.clear()
        for x, y in zip(mapping.output_values, mapping.input_values):
            self.series.append(x, y)

        self.axis_x.setRange(min(mapping.output_values), max(mapping.output_values))
        self.axis_y.setRange(min(mapping.input_values), max(mapping.input_values))
