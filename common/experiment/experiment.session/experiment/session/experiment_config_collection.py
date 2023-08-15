import re
from abc import abstractmethod, ABC
from collections.abc import MutableMapping
from typing import Optional

from experiment.configuration import ExperimentConfig


class ExperimentConfigCollection(MutableMapping[str, ExperimentConfig], ABC):
    """Interface for the set of experiment configurations in a session.

    This defines the methods that are required to implement how to access the configurations of an experiment.
    """

    def __getitem__(self, name: str) -> ExperimentConfig:
        return ExperimentConfig.from_yaml(self.get_experiment_config_yaml(name))

    @abstractmethod
    def get_experiment_config_yaml(self, name: str) -> str:
        """Get the experiment configuration yaml string.

        Args:
            name: The name of the experiment configuration.

        Returns:
            The yaml string representation of the experiment configuration.
        """

        raise NotImplementedError()

    @abstractmethod
    def add_experiment_config(
        self,
        experiment_config: ExperimentConfig,
        name: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> str:
        """Add a new experiment config to the session.

        Args:
            experiment_config: the experiment config to add to the session.
            name: an optional name to identify the experiment config. If no name is
                provided an automatic value will be generated and returned.
            comment: optional description of the experiment config to add.

        Returns:
            The value of name if provided, otherwise it will be a generated name.
        """

        ...

    def get_unused_name(self) -> str:
        numbers = []
        pattern = re.compile("config_(\\d+)")
        for name in self:
            if match := pattern.match(name):
                numbers.append(int(match.group(1)))
        return f"config_{_find_first_unused_number(numbers)}"

    @abstractmethod
    def set_current(self, name: str):
        """Set the current experiment config.

        The current experiment config is the one associated to a sequence when it is
        launched.
        """

        raise NotImplementedError()

    @abstractmethod
    def get_current(self) -> Optional[str]:
        """Get the name of the currently selected experiment config."""

        raise NotImplementedError()

    def get_current_config(self) -> Optional[ExperimentConfig]:
        """Get the current experiment configuration.

        Returns:
            The current experiment configuration if one is set, None otherwise.
        Raises:
            ValueError: If the yaml representation of the current experiment
            configuration is invalid.
        """

        experiment_config_yaml = self.get_current_experiment_config_yaml()
        if experiment_config_yaml is None:
            return None

        try:
            return ExperimentConfig.from_yaml(experiment_config_yaml)
        except Exception as e:
            name = self.get_current()
            raise ValueError(f"Failed to load experiment config '{name}'") from e

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
        experiment_config_yaml = self.get_experiment_config_yaml(name)
        return experiment_config_yaml


def _find_first_unused_number(numbers: list[int]) -> int:
    for index, value in enumerate(sorted(numbers)):
        if index != value:
            return index
    return len(numbers)


class ReadOnlyExperimentConfigError(RuntimeError):
    """Raised when trying to modify an experiment config that is attached to one or more sequences."""

    pass
