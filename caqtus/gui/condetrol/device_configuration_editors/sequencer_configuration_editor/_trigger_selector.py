from typing import Optional, assert_never

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QWidget

from caqtus.device.sequencer import (
    Trigger,
    SoftwareTrigger,
    ExternalClockOnChange,
    ExternalClock,
    ExternalTriggerStart,
)


class TriggerSelector(QComboBox):
    """A widget to select a trigger for a sequencer.

    Signals:
        trigger_changed: Emitted when the trigger is changed, either by the user or
            programmatically.
    """

    trigger_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.addItems(
            ["Software", "External start", "External clock", "External adaptive clock"]
        )
        self.setCurrentIndex(0)
        self.currentIndexChanged.connect(self._on_trigger_changed)

    def set_trigger(self, trigger: Trigger) -> None:
        """Set the trigger to be displayed."""

        match trigger:
            case SoftwareTrigger():
                self.setCurrentIndex(0)
            case ExternalTriggerStart():
                self.setCurrentIndex(1)
            case ExternalClock():
                self.setCurrentIndex(2)
            case ExternalClockOnChange():
                self.setCurrentIndex(3)
            case _:
                assert_never(trigger)

    def get_trigger(self) -> Trigger:
        """Get the trigger currently selected."""

        index = self.currentIndex()
        if index == 0:
            return SoftwareTrigger()
        elif index == 1:
            return ExternalTriggerStart()
        elif index == 2:
            return ExternalClock()
        elif index == 3:
            return ExternalClockOnChange()
        else:
            assert False

    def _on_trigger_changed(self, *args, **kwargs) -> None:
        self.trigger_changed.emit()
