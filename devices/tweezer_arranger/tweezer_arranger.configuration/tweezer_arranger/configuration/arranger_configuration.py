from abc import ABC
from typing import NewType, Generic, TypeVar, Any

from configuration_holder import ConfigurationHolder
from device.configuration import DeviceConfiguration, DeviceParameter
from device.name import DeviceName
from .tweezer_configuration import TweezerConfiguration, AODTweezerConfiguration

TweezerConfigurationName = NewType("TweezerConfigurationName", str)

TweezerConfigurationType = TypeVar(
    "TweezerConfigurationType", bound=TweezerConfiguration
)


class TweezerArrangerConfiguration(
    DeviceConfiguration,
    ConfigurationHolder[TweezerConfigurationName, TweezerConfigurationType],
    ABC,
    Generic[TweezerConfigurationType],
):
    pass


class AODTweezerArrangerConfiguration(
    TweezerArrangerConfiguration[AODTweezerConfiguration]
):
    awg_to_use: DeviceName

    def get_device_type(self) -> str:
        return "AODTweezerArranger"

    def get_device_init_args(self, *args, **kwargs) -> dict[DeviceParameter, Any]:
        raise NotImplementedError
