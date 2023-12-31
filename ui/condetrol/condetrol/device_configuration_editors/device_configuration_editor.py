import abc

from PyQt6.QtWidgets import QWidget
from core.device import DeviceConfigurationAttrs
from qabc import QABC


class DeviceConfigurationEditor[T: DeviceConfigurationAttrs](QWidget, QABC):
    @abc.abstractmethod
    def set_configuration(self, device_configuration: T) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_configuration(self) -> T:
        raise NotImplementedError
