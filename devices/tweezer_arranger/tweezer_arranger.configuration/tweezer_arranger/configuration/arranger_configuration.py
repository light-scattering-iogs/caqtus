from abc import ABC
from typing import NewType, Generic, TypeVar

from configuration_holder import ConfigurationHolder
from device.configuration import DeviceConfiguration

from .tweezer_configuration import TweezerConfiguration

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
