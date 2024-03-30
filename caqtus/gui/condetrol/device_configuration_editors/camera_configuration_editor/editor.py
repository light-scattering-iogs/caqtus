import abc
import copy
from typing import TypeVar

import caqtus.gui.qtutil.qabc as qabc
from caqtus.device.camera.configuration import CameraConfiguration

from .editor_ui import Ui_CameraConfigurationEditor
from ..configurations_editor import DeviceConfigurationEditor

T = TypeVar("T", bound=CameraConfiguration)


class CameraConfigurationEditor(
    DeviceConfigurationEditor[T], Ui_CameraConfigurationEditor, qabc.QABC
):
    @abc.abstractmethod
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.device_config = self.get_default_configuration()

    @classmethod
    @abc.abstractmethod
    def get_default_configuration(cls) -> T:
        raise NotImplementedError

    def get_configuration(self) -> T:
        self.device_config = self.update_config_from_ui(self.device_config)
        return self.device_config

    def set_configuration(self, device_configuration: T) -> None:
        self.device_config = device_configuration
        self.update_ui_from_config(self.device_config)

    @abc.abstractmethod
    def update_ui_from_config(self, device_config: T) -> None:
        self._left_spinbox.setRange(0, device_config.roi.original_width - 1)
        self._left_spinbox.setValue(device_config.roi.left)

        self._right_spinbox.setRange(0, device_config.roi.original_width - 1)
        self._right_spinbox.setValue(device_config.roi.right)

        self._bottom_spinbox.setRange(0, device_config.roi.original_height - 1)
        self._bottom_spinbox.setValue(device_config.roi.bottom)

        self._top_spinbox.setRange(0, device_config.roi.original_height - 1)
        self._top_spinbox.setValue(device_config.roi.top)

    @abc.abstractmethod
    def update_config_from_ui(self, device_config: T) -> T:
        device_config = copy.deepcopy(device_config)
        device_config.roi.x = self._left_spinbox.value()
        device_config.roi.width = (
            self._right_spinbox.value() - self._left_spinbox.value() + 1
        )
        device_config.roi.y = self._bottom_spinbox.value()
        device_config.roi.height = (
            self._top_spinbox.value() - self._bottom_spinbox.value() + 1
        )
        return device_config
