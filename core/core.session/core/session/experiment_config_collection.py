import re
from abc import abstractmethod, ABC
from collections.abc import MutableMapping
from datetime import datetime
from typing import Optional

from experiment.configuration import ExperimentConfig
from util import serialization


class ExperimentConfigCollection(MutableMapping[str, ExperimentConfig], ABC):
    """Interface for the set of experiment configurations in a session.

    This defines the methods that are required to implement how to access the configuration of devices needed to run
    the experiment.
    """

    def __getitem__(self, name: str) -> ExperimentConfig:
        """Get an experiment configuration by name.

        This method will read the serialized experiment configuration string from the session and deserialize it. If the
        deserialization fails, an exception will be raised. It might then be necessary to call the method
        `get_experiment_config_yaml` to check that the yaml string is valid.
        """

        try:
            experiment_config = serialization.from_json(
                self.get_experiment_config_json(name), ExperimentConfig
            )
        except Exception as e:
            raise ValueError(f"Failed to load experiment config '{name}'") from e
        if not isinstance(experiment_config, ExperimentConfig):
            raise TypeError(
                f"Expected an ExperimentConfig, got {type(experiment_config)}"
            )
        return experiment_config

    @abstractmethod
    def get_experiment_config_json(self, name: str) -> str:
        """Get the experiment configuration json string.

        Args:
            name: The name of the experiment configuration.

        Returns:
            The json string representation of the experiment configuration.

        Raises:
            KeyError: If there is no experiment configuration with the given name.
        """

        raise NotImplementedError()

    def __setitem__(self, name: str, experiment_config: ExperimentConfig):
        if not isinstance(name, str):
            raise TypeError(f"Expected <str> for name, got {type(name)}")
        if not isinstance(experiment_config, ExperimentConfig):
            raise TypeError(
                f"Expected <ExperimentConfig> for value, got {type(experiment_config)}"
            )
        json_config = serialization.to_json(experiment_config, ExperimentConfig)
        if serialization.from_json(json_config, ExperimentConfig) != experiment_config:
            raise AssertionError("The experiment config was not correctly serialized.")
        self._set_experiment_config_json(name, json_config)

    @abstractmethod
    def _set_experiment_config_json(self, name: str, json_config: str):
        """Set the experiment configuration yaml string.

        This is a private method that should not be called directly. Instead, the method
         `__setitem__` should be used.

        Args:
            name: The name of the experiment configuration.
            json_config: The yaml string representation of the experiment configuration.
        """

        raise NotImplementedError()

    def add_experiment_config(
        self,
        experiment_config: ExperimentConfig,
        name: Optional[str] = None,
    ) -> str:
        """Add a new experiment config to the session.

        Args:
            experiment_config: the experiment config to add to the session.
            name: an optional name to identify the experiment config. If no name is
                provided an automatic value will be generated and returned.

        Returns:
            The value of name if provided, otherwise it will be a generated name.
        """

        if name is None:
            name = self.get_unused_name()
        self[name] = experiment_config
        return name

    def get_unused_name(self) -> str:
        numbers = []
        pattern = re.compile("config_(\\d+)")
        for name in self:
            if match := pattern.match(name):
                numbers.append(int(match.group(1)))
        return f"config_{_find_first_unused_number(numbers)}"

    @abstractmethod
    def set_current_by_name(self, name: str):
        """Set the current experiment config.

        The current experiment config is the one associated to a sequence when it is
        launched.

        Args:
            name: The name of the experiment config to set as the current one. There
            must be an experiment config with this name in the session.
        """

        raise NotImplementedError()

    @abstractmethod
    def get_current(self) -> Optional[str]:
        """Get the name of the currently selected experiment config.

        Returns:
            the name of the currently selected experiment config if one is set, None
            otherwise.
        """

        raise NotImplementedError()

    def get_current_config(self) -> Optional[ExperimentConfig]:
        """Get the current experiment configuration.

        Returns:
            The current experiment configuration if one is set, None otherwise.
        Raises:
            ValueError: If the yaml representation of the current experiment
            configuration is invalid.
        """

        current_config_name = self.get_current()
        if current_config_name is None:
            return None
        else:
            return self[current_config_name]

    def set_current_config(self, config: ExperimentConfig) -> str:
        """Update the current experiment configuration.

        If the current experiment configuration is attached to a sequence, a new one
        will be created and set as the current one. If the current experiment
        configuration is not attached to a sequence, it will be updated.

        Args:
            config: The new experiment configuration to set as the current one.

        Returns:
            The name given to the current experiment configuration after the update.
        """

        current = self.get_current()
        if current is None:
            new = self.add_experiment_config(config)
            self.set_current_by_name(new)
            return new
        else:
            try:
                self[current] = config
                return current
            except ReadOnlyExperimentConfigError:
                current = self.add_experiment_config(config)
                self.set_current_by_name(current)
                return current

    def get_current_experiment_config_yaml(self) -> Optional[str]:
        """Get the yaml representation of the current experiment configuration.

        Returns:
            The yaml representation of the current experiment configuration if one is
            set, None otherwise. The yaml representation is not guaranteed to be valid
            if the way the experiment configuration is represented changed.
        """

        name = self.get_current()
        if name is None:
            return None
        experiment_config_yaml = self.get_experiment_config_json(name)
        return experiment_config_yaml

    def get_modification_date(self, name: str) -> datetime:
        """Get the modification date of an experiment config.

        Args:
            name: The name of the experiment config.

        Returns:
            The modification date of the experiment config.
        """

        raise NotImplementedError()


def _find_first_unused_number(numbers: list[int]) -> int:
    for index, value in enumerate(sorted(numbers)):
        if index != value:
            return index
    return len(numbers)


class ReadOnlyExperimentConfigError(RuntimeError):
    """Exception raised if the experiment config cannot be modified.

    It is raised when trying to modify an experiment config that is attached to one or
    more sequences.
    """

    pass
