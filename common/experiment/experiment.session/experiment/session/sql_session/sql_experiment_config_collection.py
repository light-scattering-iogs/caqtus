from datetime import datetime
from typing import Optional, TYPE_CHECKING, Iterator

import sqlalchemy.orm
from attr import frozen
from sqlalchemy import select

from experiment.configuration import ExperimentConfig
from .model import (
    ExperimentConfigModel,
    CurrentExperimentConfigModel,
)
from ..experiment_config_collection import (
    ExperimentConfigCollection,
    ReadOnlyExperimentConfigError,
)

if TYPE_CHECKING:
    from .experiment_session_sql import SQLExperimentSession


@frozen
class SQLExperimentConfigCollection(ExperimentConfigCollection):
    parent_session: "SQLExperimentSession"

    def get_experiment_config_yaml(self, name: str) -> str:
        return ExperimentConfigModel.get_config(name, self._get_sql_session())

    def __setitem__(self, name, experiment_config):
        if not isinstance(name, str):
            raise TypeError(f"Expected <str> for name, got {type(name)}")
        if not isinstance(experiment_config, ExperimentConfig):
            raise TypeError(
                f"Expected <ExperimentConfig> for value, got {type(experiment_config)}"
            )
        yaml_ = experiment_config.to_yaml()
        assert ExperimentConfig.from_yaml(yaml_) == experiment_config
        if name in self:
            if bound_sequences := self.parent_session.sequence_hierarchy.get_bound_to_experiment_config(
                name
            ):
                sequences = ", ".join(str(sequences) for sequences in bound_sequences)
                raise ReadOnlyExperimentConfigError(
                    f"Cannot overwrite experiment config '{name}' because it is bound to sequences: {sequences}."
                )
            experiment_config_model = self._query_model(name)
            experiment_config_model.experiment_config_yaml = yaml_
            experiment_config_model.modification_date = datetime.now()
            self._get_sql_session().flush()
        else:
            ExperimentConfigModel.add_config(
                name=name,
                yaml=yaml_,
                comment=None,
                session=self._get_sql_session(),
            )

    def __delitem__(self, name: str):
        if not isinstance(name, str):
            raise TypeError(f"Expected <str> for name, got {type(name)}")
        if name not in self:
            raise KeyError(f"Config '{name}' does not exist")
        if bound_sequences := self.parent_session.sequence_hierarchy.get_bound_to_experiment_config(
            name
        ):
            sequences = ", ".join(str(sequences) for sequences in bound_sequences)
            raise ReadOnlyExperimentConfigError(
                f"Cannot delete experiment config '{name}' because it is bound to sequences: {sequences}."
            )
        self._get_sql_session().delete(self._query_model(name))
        self._get_sql_session().flush()

    def __iter__(self) -> Iterator[str]:
        session = self._get_sql_session()
        query_names = session.query(ExperimentConfigModel.name)
        names = {name for name in session.scalars(query_names)}
        return iter(names)

    def __len__(self) -> int:
        return len(list(iter(self)))

    def set_current(self, name: str):
        if not isinstance(name, str):
            raise TypeError(f"Expected <str> for name, got {type(name)}")
        CurrentExperimentConfigModel.set_current_experiment_config(
            name=name, session=self._get_sql_session()
        )

    def get_current(self) -> Optional[str]:
        return CurrentExperimentConfigModel.get_current_experiment_config_name(
            session=self._get_sql_session()
        )

    def get_modification_date(self, name: str) -> datetime:
        return self._query_model(name).modification_date

    def _query_model(self, name: str) -> ExperimentConfigModel:
        query = select(ExperimentConfigModel).where(ExperimentConfigModel.name == name)
        result = self._get_sql_session().scalar(query)
        if result is None:
            raise KeyError(f"Config {name} does not exist")
        return result

    def _get_sql_session(self) -> sqlalchemy.orm.Session:
        # noinspection PyProtectedMember
        return self.parent_session._get_sql_session()
