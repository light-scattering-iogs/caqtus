from datetime import datetime
from typing import Optional, TYPE_CHECKING, Iterator

import sqlalchemy.orm
from attr import frozen
from sqlalchemy import select

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

    def get_experiment_config_json(self, name: str) -> str:
        return ExperimentConfigModel.get_config(name, self._get_sql_session())

    def _set_experiment_config_json(self, name: str, json_config: str):
        if name in self:
            bound_sequences = (
                self.parent_session.sequence_hierarchy.get_bound_to_experiment_config(
                    name
                )
            )
            if bound_sequences:
                sequences = ", ".join(str(sequences) for sequences in bound_sequences)
                raise ReadOnlyExperimentConfigError(
                    f"Cannot overwrite experiment config '{name}' because the following sequences depend on it: "
                    f"{sequences}."
                )
            experiment_config_model = self._query_model(name)
            experiment_config_model.experiment_config_yaml = json_config
            experiment_config_model.modification_date = datetime.now()
            self._get_sql_session().flush()
        else:
            ExperimentConfigModel.add_config(
                name=name,
                yaml=json_config,
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

    def __contains__(self, item: str):
        # Here we redefine __contains__ because the default implementation of MutableMapping.__contains__ calls
        # __getitem__ which is slow since we need to deserialize the associated experiment config.
        if not isinstance(item, str):
            raise TypeError(f"Expected <str> for item, got {type(item)}")
        query = select(ExperimentConfigModel.name).where(
            ExperimentConfigModel.name == item
        )
        return self._get_sql_session().execute(query).one_or_none() is not None

    def set_current_by_name(self, name: str):
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
