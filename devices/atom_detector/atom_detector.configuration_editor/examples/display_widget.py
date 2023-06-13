import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from atom_detector.configuration import AtomDetectorConfiguration
from atom_detector.configuration_editor import AtomDetectorConfigEditor

config_path = Path(__file__).parent / "config.yaml"

with open(config_path) as f:
    config: AtomDetectorConfiguration = AtomDetectorConfiguration.from_yaml(f.read())

app = QApplication(sys.argv)
editor = AtomDetectorConfigEditor(config, [])
editor.show()
app.exec()
print(editor.get_device_config().to_yaml())
