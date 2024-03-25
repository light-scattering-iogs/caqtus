from __future__ import annotations

import abc
from typing import Optional

import polars
from PyQt6.QtWidgets import QWidget

import caqtus.gui.common.qabc as qabc


class ViewCreator(qabc.QABC):
    """Interface for a class the creates a new view over data.

    In the graphplot application, the user can select which view creator to use for creating a new view. If a view
    creator is selected by the user, the graphplot main window will call the create_view method of the view creator and
    set the returned view its central widget.
    If the view creator is a QWidget, it will be displayed in the main window in the view creator settings group so that
    users can interact with the view creator. If the view creator is not a QWidget, the settings group will be hidden.
    """

    @abc.abstractmethod
    def create_view(self) -> DataView:
        """Create a new view.

        This method will be called when the user selects a new view in the graphplot main window. The view should be
        created and returned. The view will be displayed in the main window. The main window will take ownership of the
        view.
        """

        raise NotImplementedError()


class DataView(QWidget, qabc.QABC):
    """Interface for widget that displays of view over data.

    The main widget of the graphplot application is a DataView. User can select which DataView to display in the main
    window. The DataView is responsible for displaying the data in a meaningful way.
    """

    @abc.abstractmethod
    def update_data(self, dataframe: Optional[polars.DataFrame]) -> None:
        """Update the view with the given data.

        This method will be called automatically by the graphplot main window when new data is available. The data is
        provided as a polars DataFrame, which is a table-like data structure.
        This method will always be called from the main GUI thread, so it is safe to update the GUI from this method.
        However, it is recommended to make this method as fast as possible, otherwise the GUI will become unresponsive.
        """

        raise NotImplementedError()
