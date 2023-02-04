import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtQuick import QQuickView
from PyQt6.QtQuickWidgets import QQuickWidget
from PyQt6.QtWidgets import QWidget, QHBoxLayout

from experiment_config import ExperimentConfig
from ..config_settings_editor import ConfigSettingsEditor

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class SpincoreConfigEditor(ConfigSettingsEditor):
    def __init__(
        self,
        experiment_config: ExperimentConfig,
        tree_label: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(experiment_config, tree_label, parent)
        self.config = experiment_config

        self.view = QQuickView()
        qml_path = Path(__file__).parent / "test.qml"
        self.view.setSource(QUrl.fromLocalFile(str(qml_path)))
        self.view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)

        self.view.statusChanged.connect(self.on_status_changed)

        self.layout = QHBoxLayout()
        self.setLayout(self.layout)
        widget = QWidget.createWindowContainer(self.view)
        widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.layout.addWidget(widget, 1)
        self.layout.addStretch(1)

    def get_experiment_config(self) -> ExperimentConfig:
        return self.config

    def on_status_changed(self, status: QQuickWidget.Status):
        if status == QQuickWidget.Status.Error:
            for error in self.view.errors():
                raise RuntimeError(error.toString())
