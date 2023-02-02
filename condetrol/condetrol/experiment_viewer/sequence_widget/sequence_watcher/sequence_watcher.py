from contextlib import contextmanager
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, QFileSystemWatcher

from sequence import SequenceConfig, SequenceStats
from sequence.sequence import Sequence
from settings_model import YAMLSerializable


class SequenceWatcher(QObject):
    """
    Monitors a sequence folder and emit signals when the sequence config or state change
    """

    config_changed = pyqtSignal(SequenceConfig)
    stats_changed = pyqtSignal(SequenceStats)

    def __init__(self, sequence_path: Path):
        super().__init__()
        self.config_path = Sequence.get_config_path(sequence_path)
        self.state_path = Sequence.get_stats_path(sequence_path)

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
        return YAMLSerializable.load(self.config_path)

    def read_stats(self) -> SequenceStats:
        result = YAMLSerializable.load(self.state_path)
        return result

    def _update_config(self, *args):
        self.config_changed.emit(self.read_config())

    def _update_stats(self, *args):
        self.stats_changed.emit(self.read_stats())

    @contextmanager
    def block_signals(self):
        self.sequence_config_watcher.removePath(str(self.config_path))
        try:
            yield
        finally:
            self.sequence_config_watcher.addPath(str(self.config_path))
