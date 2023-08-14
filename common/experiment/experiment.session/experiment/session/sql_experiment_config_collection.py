from datetime import datetime
from typing import Optional, TYPE_CHECKING, Iterator

import sqlalchemy.orm
from attr import frozen

from experiment.configuration import ExperimentConfig
from sql_model.model import (
    ExperimentConfigModel,
    CurrentExperimentConfigModel,
)
from .experiment_config_collection import ExperimentConfigCollection

if TYPE_CHECKING:
    from .experiment_session_sql import SQLExperimentSession


@frozen
class SQLExperimentConfigCollection(ExperimentConfigCollection):
    parent_session: "SQLExperimentSession"

    def __getitem__(self, name: str) -> ExperimentConfig:
        return ExperimentConfig.from_yaml(
            ExperimentConfigModel.get_config(name, self._get_sql_session())
        )

    def __iter__(self) -> Iterator[str]:
        session = self._get_sql_session()
        query_names = session.query(ExperimentConfigModel.name)
        names = {name for name in session.scalars(query_names)}
        return iter(names)

    def __len__(self) -> int:
        return len(list(iter(self)))

    def get_experiment_config_yamls(
        self, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None
    ) -> dict[str, str]:
        results = ExperimentConfigModel.get_configs(
            from_date,
            to_date,
            self._get_sql_session(),
        )
        return {name: yaml_ for name, yaml_ in results.items()}

    def add_experiment_config(
        self,
        experiment_config: ExperimentConfig,
        name: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> str:
        if name is None:
            name = self._get_new_experiment_config_name()
        yaml_ = experiment_config.to_yaml()
        assert ExperimentConfig.from_yaml(yaml_) == experiment_config
        ExperimentConfigModel.add_config(
            name=name,
            yaml=yaml_,
            comment=comment,
            session=self._get_sql_session(),
        )
        return name

    def set_current_experiment_config(self, name: str):
        if not isinstance(name, str):
            raise TypeError(f"Expected <str> for name, got {type(name)}")
        CurrentExperimentConfigModel.set_current_experiment_config(
            name=name, session=self._get_sql_session()
        )

    def get_current_experiment_config_name(self) -> Optional[str]:
        return CurrentExperimentConfigModel.get_current_experiment_config_name(
            session=self._get_sql_session()
        )

    def _get_sql_session(self) -> sqlalchemy.orm.Session:
        # noinspection PyProtectedMember
        return self.parent_session._get_sql_session()
