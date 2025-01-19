# pyright: strict
from __future__ import annotations

from collections.abc import Mapping
from typing import assert_never, Any

import attrs
from PySide6 import QtWidgets

from caqtus.device import DeviceName, DeviceConfiguration

type RequestedState = IntoNoSequenceSet | IntoDraftSequence
"""Describes the state of a SequenceDevicesEditor widget."""

type InternalState = NoSequenceSet | DraftSequence


@attrs.frozen
class IntoNoSequenceSet:
    """The widget is in a state where no sequence has been set."""

    pass


@attrs.frozen
class IntoDraftSequence:
    """The widget is in a state where the sequence devices can be edited."""

    device_configurations: Mapping[DeviceName, DeviceConfiguration[Any]]


@attrs.frozen
class NoSequenceSet:
    pass


@attrs.frozen
class DraftSequence:
    def device_configurations(self) -> Mapping[DeviceName, DeviceConfiguration[Any]]:
        raise NotImplementedError


class SequenceDevicesEditor(QtWidgets.QWidget):
    """A widget for displaying and editing the device configurations of a sequence."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)

        self._layout = QtWidgets.QVBoxLayout()
        self._tab_widget = QtWidgets.QTabWidget()
        clear_and_disable_tab_widget(self._tab_widget)

        self._setup_ui()

        self._state: InternalState = NoSequenceSet()

    def _setup_ui(self) -> None:
        self.setLayout(self._layout)
        self._layout.addWidget(self._tab_widget)

    def transition(self, state: RequestedState) -> None:
        """Changes the state of the widget to the given state.

        Changes the state of the widget to the given state.
        """

        new_state = None

        match state:
            case IntoNoSequenceSet():
                clear_and_disable_tab_widget(self._tab_widget)
                new_state = NoSequenceSet()
            case IntoDraftSequence():
                raise NotImplementedError
            case _:
                assert_never(state)

        self._state = new_state

    def state(self) -> InternalState:
        """The current state of the widget.

        Returns:
            A reference to the current state of the widget.
            The value returned becomes invalid whenever a method changing the widget's
            state is called.
        """

        return self._state


def delete_all_tabs(tab_widget: QtWidgets.QTabWidget) -> None:
    """Removes all tabs from the tab widget and deletes the widgets they contain."""

    while tab_widget.count() > 0:
        tab_widget.widget(0).deleteLater()
        tab_widget.removeTab(0)


def clear_and_disable_tab_widget(tab_widget: QtWidgets.QTabWidget) -> None:
    tab_widget.setEnabled(False)
    delete_all_tabs(tab_widget)
