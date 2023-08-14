import re
from abc import abstractmethod, ABC
from collections.abc import Mapping
from datetime import datetime
from typing import Optional

from experiment.configuration import ExperimentConfig


class ExperimentConfigCollection(Mapping[str, ExperimentConfig], ABC):
    def get_experiment_configs(
        self, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None
    ) -> dict[str, ExperimentConfig]:
        """Get the experiment configurations available within the session.

        Args:
            from_date: Only query experiment configurations that were modified
                after this date.
            to_date: Only query experiment configurations that were modified before
                this date.

        Returns:
            A dictionary mapping experiment configuration names to the corresponding
            ExperimentConfig object.

        Raises:
            ValueError: If the yaml representation of an experiment configuration is
                invalid.
        """

        raw_yamls = self.get_experiment_config_yamls(from_date, to_date)
        results = {}

        for name, yaml_ in raw_yamls.items():
            try:
                results[name] = ExperimentConfig.from_yaml(yaml_)
            except Exception as e:
                raise ValueError(f"Failed to load experiment config '{name}'") from e

        return results

    @abstractmethod
    def get_experiment_config_yamls(
        self, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None
    ) -> dict[str, str]:
        """Get the experiment configuration raw yaml strings.

        Args:
            from_date: Only query experiment configurations that were modified
                after this date.
            to_date: Only query experiment configurations that were modified before
                this date.

        Returns:
            A dictionary mapping experiment configuration names to their yaml string
            representation. The yaml representations are not guaranteed to be valid if
            the way the experiment configuration is represented changes.
        """

        ...

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

    def _get_new_experiment_config_name(self) -> str:
        numbers = []
        pattern = re.compile("config_(\\d+)")
        for name in self:
            if match := pattern.match(name):
                numbers.append(int(match.group(1)))
        return f"config_{_find_first_unused_number(numbers)}"

    @abstractmethod
    def set_current_experiment_config(self, name: str):
        """Set the current experiment config.

        The current experiment config is the one associated to a sequence when it is
        launched.
        """

        raise NotImplementedError()

    @abstractmethod
    def get_current_experiment_config_name(self) -> Optional[str]:
        """Get the name of the currently selected experiment config."""

        raise NotImplementedError()

    def get_current_experiment_config_yaml(self) -> Optional[str]:
        """Get the yaml representation of the current experiment configuration.

        Returns:
            The yaml representation of the current experiment configuration if one is
            set, None otherwise. The yaml representation is not guaranteed to be valid
            if the way the experiment configuration is represented changed.
        """

        name = self.get_current_experiment_config_name()
        if name is None:
            return None
        experiment_config_yaml = self.get_experiment_config_yamls()[name]
        return experiment_config_yaml

    def get_current_experiment_config(self) -> Optional[ExperimentConfig]:
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
            name = self.get_current_experiment_config_name()
            raise ValueError(f"Failed to load experiment config '{name}'") from e


def _find_first_unused_number(numbers: list[int]) -> int:
    for index, value in enumerate(sorted(numbers)):
        if index != value:
            return index
    return len(numbers)
