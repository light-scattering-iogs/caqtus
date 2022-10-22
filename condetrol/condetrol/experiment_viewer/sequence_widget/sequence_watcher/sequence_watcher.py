from pathlib import Path

import yaml
from PyQt5.QtCore import QObject, pyqtSignal, QFileSystemWatcher

from sequence import SequenceConfig, SequenceStats
from settings_model import YAMLSerializable


class SequenceWatcher(QObject):
    """
    Monitors a sequence folder and emit signals when the sequence config or state change
    """

    config_changed = pyqtSignal(SequenceConfig)
    stats_changed = pyqtSignal(SequenceStats)

    def __init__(self, sequence_path: Path):
        super().__init__()
        self.config_path = sequence_path / "sequence_config.yaml"
        self.state_path = sequence_path / "sequence_state.yaml"

        self.sequence_config_watcher = QFileSystemWatcher()
        self.sequence_config_watcher.addPath(str(self.config_path))
        self.sequence_config_watcher.fileChanged.connect(self._update_config)

        self.sequence_state_watcher = QFileSystemWatcher()
        self.sequence_state_watcher.addPath(str(self.state_path))
        self.sequence_state_watcher.fileChanged.connect(self._update_stats)
        self.sequence_state_watcher.fileChanged.emit(
            self.sequence_state_watcher.files()[0]
        )

    def read_config(self) -> SequenceConfig:
        with open(self.config_path, "r") as file:
            return yaml.load(file, Loader=YAMLSerializable.get_loader())

    def read_stats(self) -> SequenceStats:
        with open(self.state_path, "r") as file:
            return yaml.load(file.read(), Loader=YAMLSerializable.get_loader())

    def _update_config(self, *args):
        self.config_changed.emit(self.read_config())

    def _update_stats(self, *args):
        self.stats_changed.emit(self.read_stats())
