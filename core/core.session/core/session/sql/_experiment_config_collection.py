from datetime import datetime
from typing import Optional, TYPE_CHECKING, Iterator

import sqlalchemy.orm
from attr import frozen
from sqlalchemy import select
import json

from ._tables import ExperimentConfig, CurrentExperimentConfig

from ..experiment_config_collection import (
    ExperimentConfigCollection,
    ReadOnlyExperimentConfigError,
)

if TYPE_CHECKING:
    from ._experiment_session import SQLExperimentSession


@frozen
class SQLExperimentConfigCollection(ExperimentConfigCollection):
    parent_session: "SQLExperimentSession"

    def get_experiment_config_json(self, name: str) -> str:
        obj = ExperimentConfig.get_config(name, self._get_sql_session())
        return json.dumps(obj)

    def _set_experiment_config_json(self, name: str, json_config: str):
        obj = json.loads(json_config)
        if name in self:
            bound_sequences = (
                self.parent_session.sequence_hierarchy.get_bound_to_experiment_config(
                    name
                )
            )
            if bound_sequences:
                sequences = ", ".join(str(sequences) for sequences in bound_sequences)
                raise ReadOnlyExperimentConfigError(
                    f"Cannot overwrite experiment config '{name}' because the following"
                    f" sequences depend on it: {sequences}."
                )
            experiment_config_model = self._query_model(name)
            experiment_config_model.content = obj
            experiment_config_model.modification_date = datetime.now()
            self._get_sql_session().flush()
        else:
            ExperimentConfig.add_config(
                name=name,
                content=obj,
                comment=None,
                session=self._get_sql_session(),
            )

    def __delitem__(self, name: str):
        if not isinstance(name, str):
            raise TypeError(f"Expected <str> for name, got {type(name)}")
        if name not in self:
            raise KeyError(f"Config '{name}' does not exist")
        bound_sequences = (
            self.parent_session.sequence_hierarchy.get_bound_to_experiment_config(name)
        )
        if bound_sequences:
            sequences = ", ".join(str(sequences) for sequences in bound_sequences)
            raise ReadOnlyExperimentConfigError(
                f"Cannot delete experiment config '{name}' because it is bound to "
                f"sequences: {sequences}."
            )
        self._get_sql_session().delete(self._query_model(name))
        self._get_sql_session().flush()

    def __iter__(self) -> Iterator[str]:
        session = self._get_sql_session()
        query_names = select(ExperimentConfig.name)
        names = {name for name in session.scalars(query_names)}
        return iter(names)

    def __len__(self) -> int:
        return len(list(iter(self)))

    def __contains__(self, item: str):
        # Here we redefine __contains__ because the default implementation of
        # MutableMapping.__contains__ calls __getitem__ which is slow since we need to
        # deserialize the associated experiment config.
        if not isinstance(item, str):
            raise TypeError(f"Expected <str> for item, got {type(item)}")
        query = select(ExperimentConfig.name).where(ExperimentConfig.name == item)
        return self._get_sql_session().execute(query).one_or_none() is not None

    def set_current_by_name(self, name: str):
        if not isinstance(name, str):
            raise TypeError(f"Expected <str> for name, got {type(name)}")
        CurrentExperimentConfig.set_current_experiment_config(
            name=name, session=self._get_sql_session()
        )

    def get_current_by_name(self) -> Optional[str]:
        return CurrentExperimentConfig.get_current_experiment_config_name(
            session=self._get_sql_session()
        )

    def get_modification_date(self, name: str) -> datetime:
        return self._query_model(name).modification_date

    def _query_model(self, name: str) -> ExperimentConfig:
        query = select(ExperimentConfig).where(ExperimentConfig.name == name)
        result = self._get_sql_session().scalar(query)
        if result is None:
            raise KeyError(f"Config {name} does not exist")
        return result

    def _get_sql_session(self) -> sqlalchemy.orm.Session:
        # noinspection PyProtectedMember
        return self.parent_session._get_sql_session()
