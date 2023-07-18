import datetime
from abc import ABC
from typing import NewType, Generic, TypeVar, Any

from device.configuration import DeviceConfiguration, DeviceParameter
from device.name import DeviceName
from settings_model import SettingsModel
from .tweezer_configuration import TweezerConfiguration, AODTweezerConfiguration

TweezerConfigurationName = NewType("TweezerConfigurationName", str)

TweezerConfigurationType = TypeVar(
    "TweezerConfigurationType", bound=TweezerConfiguration
)


class TweezerConfigurationInfo(SettingsModel, Generic[TweezerConfigurationType]):
    configuration: TweezerConfigurationType
    modification_date: datetime.datetime


class TweezerArrangerConfiguration(
    DeviceConfiguration, Generic[TweezerConfigurationType], ABC
):
    tweezer_configurations: dict[
        TweezerConfigurationName, TweezerConfigurationInfo[TweezerConfigurationType]
    ]


class AODTweezerArrangerConfiguration(
    TweezerArrangerConfiguration[AODTweezerConfiguration]
):
    tweezer_configurations: dict[
        TweezerConfigurationName, TweezerConfigurationInfo[AODTweezerConfiguration]
    ]
    awg_to_use: DeviceName

    def get_device_type(self) -> str:
        return "AODTweezerArranger"

    def get_device_init_args(self, *args, **kwargs) -> dict[DeviceParameter, Any]:
        raise NotImplementedError
