import logging
from abc import abstractmethod
from typing import Any

from PyQt6.QtGui import QShortcut, QKeySequence, QGuiApplication, QClipboard

from qabc import QABC
from settings_model import YAMLSerializable

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class YAMLClipboardMixin(QABC):
    """A mixin that adds copy and paste shortcuts to and from yaml text on the clipboard

    Subclasses must implement methods to indicate what must be (de)serialized to/from external applications.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._copy_shortcut = QShortcut(QKeySequence("Ctrl+Alt+C"), self)
        self._copy_shortcut.activated.connect(self._copy)

        self._paste_shortcut = QShortcut(QKeySequence("Ctrl+Alt+V"), self)
        self._paste_shortcut.activated.connect(self._paste)

    def _copy(self):
        text = YAMLSerializable.dump(self.convert_to_external_use())
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(text, mode=QClipboard.Mode.Clipboard)
        logger.info(f"Copied to clipboard")

    def _paste(self):
        text = QGuiApplication.clipboard().text(mode=QClipboard.Mode.Clipboard)
        external_source = YAMLSerializable.load(text)
        self.update_from_external_source(external_source)
        logger.info(f"Pasted from clipboard")

    @abstractmethod
    def convert_to_external_use(self) -> Any:
        """Convert the internal representation to an abject that can be serialized to yaml"""
        ...

    @abstractmethod
    def update_from_external_source(self, external_source: Any):
        """Update the internal representation from an object that was deserialized from yaml"""
        ...
