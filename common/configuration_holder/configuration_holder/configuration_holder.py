from datetime import datetime
from typing import Generic, TypeVar, MutableMapping

from settings_model import SettingsModel
from validate_arguments import validate_arguments

_T = TypeVar("_T")
_K = TypeVar("_K")


class ConfigurationInfo(Generic[_T], SettingsModel):
    configuration: _T
    creation_date: datetime
    modification_date: datetime


class ConfigurationHolder(SettingsModel, Generic[_K, _T], MutableMapping[_K, _T]):
    """Holds several configuration with their creation and modification dates.

    This class behaves like a mutable mapping from configuration names to configurations that also records the creation
    and modification dates of each configuration. This is typically used to store the information for a device that can
    be used in many user defined configurations.
    """

    configurations: dict[_K, ConfigurationInfo[_T]]

    def _get_configuration_info(self, configuration_name: _K) -> ConfigurationInfo[_T]:
        try:
            return self.configurations[configuration_name]
        except KeyError:
            raise KeyError(
                f"There is no configuration matching the name '{configuration_name}'"
            )

    def __getitem__(self, configuration_name: _K) -> _T:
        """Return a copy of the configuration associated with a given name."""

        return self._get_configuration_info(configuration_name).configuration

    @validate_arguments
    def __setitem__(self, configuration_name: _K, configuration: _T):
        """Set the value of a detector configuration at a given name."""

        if configuration_name not in self.configurations:
            self.configurations[configuration_name] = ConfigurationInfo(
                configuration=configuration,
                creation_date=datetime.now(),
                modification_date=datetime.now(),
            )
        else:
            self.configurations[configuration_name].configuration = configuration
            self.configurations[configuration_name].modification_date = datetime.now()

    def __delitem__(self, configuration_name: _K):
        """Remove a configuration from the configuration dictionary."""

        del self.configurations[configuration_name]

    def __iter__(self):
        return iter(self.configurations)

    def __len__(self) -> int:
        return len(self.configurations)

    def get_modification_date(self, configuration_name: _K) -> datetime:
        return self._get_configuration_info(configuration_name).modification_date
