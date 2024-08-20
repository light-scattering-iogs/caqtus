from collections.abc import Set
from typing import Optional, Literal

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QWidget

from caqtus.device.sequencer.trigger import (
    Trigger,
    SoftwareTrigger,
    ExternalClockOnChange,
    ExternalClock,
    ExternalTriggerStart,
)

AvailableTriggers = Literal[
    "Software", "External start", "External clock", "External adaptive clock"
]

DEFAULT_AVAILABLE_TRIGGERS = frozenset(
    [
        "Software",
        "External start",
        "External clock",
        "External adaptive clock",
    ]
)


class TriggerSelector(QComboBox):
    """A widget to select a trigger for a sequencer.

    Args:
        available_triggers: The triggers that can be selected.

            If a device does not support all trigger types, the triggers proposed by
            the editor can be limited by providing a subset of the available triggers.

            The default is all available triggers.

        parent: The parent widget.

    Signals:
        trigger_changed: Emitted when the trigger is changed, either by the user or
            programmatically.
    """

    trigger_changed = Signal()

    def __init__(
        self,
        available_triggers: Set[AvailableTriggers] = DEFAULT_AVAILABLE_TRIGGERS,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        proposed_triggers = sorted(available_triggers)
        self.tags_to_index = {tag: index for index, tag in enumerate(proposed_triggers)}
        self.index_to_tag = {index: tag for index, tag in enumerate(proposed_triggers)}
        self.addItems(proposed_triggers)
        self.currentIndexChanged.connect(self._on_trigger_changed)

    def set_trigger(self, trigger: Trigger) -> None:
        """Set the trigger to be displayed."""

        trigger_to_tag = {
            SoftwareTrigger: "Software",
            ExternalTriggerStart: "External start",
            ExternalClock: "External clock",
            ExternalClockOnChange: "External adaptive clock",
        }

        try:
            trigger_tag = trigger_to_tag[type(trigger)]
        except KeyError:
            raise ValueError(f"Unsupported trigger: {trigger}")

        try:
            trigger_index = self.tags_to_index[trigger_tag]
        except KeyError:
            raise ValueError(f"Unsupported trigger: {trigger}")

        self.setCurrentIndex(trigger_index)

    def get_trigger(self) -> Trigger:
        """Get the trigger currently selected."""

        index = self.currentIndex()

        trigger_tag = self.index_to_tag[index]

        tag_to_trigger = {
            "Software": SoftwareTrigger,
            "External start": ExternalTriggerStart,
            "External clock": ExternalClock,
            "External adaptive clock": ExternalClockOnChange,
        }

        return tag_to_trigger[trigger_tag]()

    def _on_trigger_changed(self, *args, **kwargs) -> None:
        self.trigger_changed.emit()
