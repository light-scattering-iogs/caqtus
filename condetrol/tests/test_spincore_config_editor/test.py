import os
import sys
from pathlib import Path

import qdarkstyle
from PyQt6.QtTest import QTest


from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication

from condetrol.experiment_viewer.config_editor.spincore_config_editor import (
    SpincoreConfigEditor,
)
from experiment_config import ExperimentConfig

with open(Path(__file__).parent / "config.yaml", "r") as file:
    config = ExperimentConfig.from_yaml(file.read())

if __name__ == "__main__":
    os.environ["QT_QUICK_CONTROLS_CONF"] = "C:\\Users\\Damien Bloch\\Desktop\\caqtus_repo\\condetrol\\qtquickcontrols2.conf"
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(qdarkstyle.load_stylesheet())

    spincore_editor = SpincoreConfigEditor(
        config, "Devices\\Spincore PulseBlaster sequencer"
    )

    spincore_editor.showMaximized()

    app.exec()
