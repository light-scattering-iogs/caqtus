from __future__ import annotations

from collections.abc import Mapping, Callable
from typing import assert_never

import attrs
from PySide6 import QtWidgets

from caqtus.device import DeviceName, DeviceConfiguration
from caqtus.gui.condetrol.device_configuration_editors import DeviceConfigurationEditor
from caqtus.utils import with_note

type WidgetState = NoSequenceSet | DraftSequence
"""Describes the state of a SequenceDevicesEditor widget."""


@attrs.frozen
class NoSequenceSet:
    """The widget is in a state where no sequence has been set."""

    pass


@attrs.frozen
class DraftSequence:
    """The widget is in a state where the sequence devices can be edited."""

    device_configurations: Mapping[DeviceName, DeviceConfiguration]


class SequenceDevicesEditor(QtWidgets.QWidget):
    """A widget for displaying and editing the device configurations of a sequence."""

    type _InternalState = (
        SequenceDevicesEditor._NoSequenceSet | SequenceDevicesEditor._DraftSequence
    )

    def __init__(
        self,
        device_editor_factory: Callable[
            [DeviceConfiguration], DeviceConfigurationEditor
        ],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._device_editor_factory = device_editor_factory
        self._layout = QtWidgets.QVBoxLayout()
        self.tab_widget = QtWidgets.QTabWidget()
        clear_and_disable_tab_widget(self.tab_widget)

        self._setup_ui()

        self._state: SequenceDevicesEditor._InternalState = self._NoSequenceSet(self)

    def _setup_ui(self) -> None:
        self.setLayout(self._layout)
        self._layout.addWidget(self.tab_widget)

    def set_fresh_state(self, state: WidgetState) -> None:
        """Changes the state of the widget to the given state.

        This method discards the current state of the widget and replaces it with the
        given state.
        """

        match state:
            case NoSequenceSet():
                new_state = self._NoSequenceSet.create_fresh(self)
            case DraftSequence():
                new_state = self._DraftSequence.create_fresh(self, state)
            case _:
                assert_never(state)

        self._state = new_state

    def state(self) -> WidgetState:
        """The current state of the widget.

        Returns:
            A reference to the current state of the widget.
            The value returned becomes invalid whenever a method changing the widget's
            state is called.
        """

        return self._state.read()

    @attrs.frozen
    class _NoSequenceSet:
        parent: SequenceDevicesEditor

        @classmethod
        def create_fresh(
            cls, parent: SequenceDevicesEditor
        ) -> SequenceDevicesEditor._NoSequenceSet:
            clear_and_disable_tab_widget(parent.tab_widget)
            return cls(parent)

        def read(self) -> NoSequenceSet:
            return NoSequenceSet()

    @attrs.frozen
    class _DraftSequence:
        parent: SequenceDevicesEditor

        @classmethod
        def create_fresh(
            cls, parent: SequenceDevicesEditor, state: DraftSequence
        ) -> SequenceDevicesEditor._DraftSequence:
            delete_all_tabs(parent.tab_widget)
            for name, config in state.device_configurations.items():
                editor = parent._device_editor_factory(config)
                editor.set_configuration(config)
                parent.tab_widget.addTab(editor, name)
            parent.tab_widget.setTabsClosable(True)
            parent.tab_widget.setEnabled(True)
            return cls(parent)

        def read(self) -> DraftSequence:
            configurations = dict[DeviceName, DeviceConfiguration]()
            for widget_index in range(self.parent.tab_widget.count()):
                widget = self.parent.tab_widget.widget(widget_index)
                name = self.parent.tab_widget.tabText(widget_index)
                assert isinstance(widget, DeviceConfigurationEditor)
                config = widget.get_configuration()
                if not isinstance(config, DeviceConfiguration):
                    raise with_note(
                        AssertionError(
                            f"{widget.get_configuration} returned {config!r} instead "
                            f"of a DeviceConfiguration."
                        ),
                        f"This means that the extension providing {type(widget)} needs "
                        f"to be fixed.",
                    )
                configurations[DeviceName(name)] = config
            return DraftSequence(device_configurations=configurations)


def delete_all_tabs(tab_widget: QtWidgets.QTabWidget) -> None:
    """Removes all tabs from the tab widget and deletes the widgets they contain."""

    while tab_widget.count() > 0:
        tab_widget.widget(0).deleteLater()
        tab_widget.removeTab(0)


def clear_and_disable_tab_widget(tab_widget: QtWidgets.QTabWidget) -> None:
    tab_widget.setEnabled(False)
    delete_all_tabs(tab_widget)
