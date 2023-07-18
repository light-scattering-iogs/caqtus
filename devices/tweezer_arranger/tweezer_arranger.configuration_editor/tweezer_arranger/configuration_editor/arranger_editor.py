import logging
from typing import Collection, Optional

import mplcursors
from PyQt6.QtCore import QAbstractListModel, QModelIndex, Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qt import NavigationToolbar2QT
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from device.configuration_editor import DeviceConfigEditor
from device_server.name import DeviceServerName
from tweezer_arranger.configuration import (
    TweezerArrangerConfiguration,
    TweezerConfigurationName,
    TweezerConfiguration,
    TweezerConfiguration2D,
)
from .configuration_editor_ui import Ui_TweezerArrangerConfigEditor

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class TweezerArrangerConfigEditor(
    Ui_TweezerArrangerConfigEditor, DeviceConfigEditor[TweezerArrangerConfiguration]
):
    """Widget to display the configurations of a tweezer arranger.

    This widget doesn't allow to edit the configurations, only to display them.
    """

    def __init__(
        self,
        device_config: TweezerArrangerConfiguration,
        available_remote_servers: Collection[DeviceServerName],
        *args,
        **kwargs,
    ):
        super().__init__(device_config, available_remote_servers, *args, **kwargs)
        self.setupUi(self)
        self.update_ui(device_config)
        self._view_widget = TweezerConfigurationWidget()
        self.list_view.clicked.connect(self.on_configuration_clicked)
        self.layout().addWidget(self._view_widget)

    def on_configuration_clicked(self, index: QModelIndex):
        if not index.isValid():
            return
        name = self.list_view.model().data(index, Qt.ItemDataRole.DisplayRole)
        tweezer_config = self._device_config[name]
        self._view_widget.update_ui(tweezer_config)

    def get_device_config(self) -> TweezerArrangerConfiguration:
        return self.list_view.model().config

    def update_ui(self, device_config: TweezerArrangerConfiguration):
        self.list_view.setModel(ArrangerModel(device_config))


class ArrangerModel(QAbstractListModel):
    def __init__(self, config: TweezerArrangerConfiguration, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.config = config

    @property
    def config(self) -> TweezerArrangerConfiguration:
        return self._config

    @config.setter
    def config(self, device_config: TweezerArrangerConfiguration) -> None:
        self.beginResetModel()
        self._config = device_config
        self._config_names = list(device_config.configurations)
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._config_names)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        name = self._config_names[index.row()]
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return name
        elif role == Qt.ItemDataRole.ToolTipRole:
            modification_date = self._config.get_modification_date(name)
            tweezer_config = self._config[name]
            return (
                f"Number tweezers: {tweezer_config.number_tweezers}\n"
                f"Modification date: {modification_date:%Y-%m-%d %H:%M:%S}"
            )

        return None

    def setData(
        self, index: QModelIndex, value: str, role: int = Qt.ItemDataRole.EditRole
    ) -> bool:
        if not index.isValid():
            return False
        if role == Qt.ItemDataRole.EditRole:
            new_name = TweezerConfigurationName(value)
            old_name = self._config_names[index.row()]
            config = self._config[old_name]
            del self._config[old_name]
            self._config[new_name] = config
            self._config_names[index.row()] = new_name
            return True
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEditable
        )


class TweezerConfigurationWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()
        self._cursors: list[mplcursors.Cursor] = []

    def _setup_ui(self) -> None:
        self._figure = Figure()
        self._axes = self._figure.add_subplot()
        self._axes.set_aspect("equal")
        self._canvas = FigureCanvasQTAgg(self._figure)

        self.setLayout(QVBoxLayout())
        navigation_toolbar = NavigationToolbar2QT(self._canvas, self)
        self.layout().addWidget(navigation_toolbar)
        self.layout().addWidget(self._canvas)

    def update_ui(self, tweezer_config: TweezerConfiguration) -> None:
        self._axes.clear()
        units = tweezer_config.position_units
        self._axes.set_xlabel(f"x [{units}]")
        self._axes.set_ylabel(f"y [{units}]")
        if not isinstance(tweezer_config, TweezerConfiguration2D):
            raise NotImplementedError(
                f"Only 2D configurations are supported, got {type(tweezer_config)}"
            )
        self._cursors = []
        for label, position in tweezer_config.tweezer_positions().items():

            cursor = mplcursors.Cursor(
                [self._axes.scatter(position[0], position[1], color="black", label=label)],
                hover=mplcursors.HoverMode.Transient,
                highlight=True
            )
            self._cursors.append(cursor)
        self._canvas.draw()
