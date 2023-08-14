from collections.abc import Mapping
from datetime import datetime
from threading import Lock
from typing import Optional

import sqlalchemy.orm
from attrs import define

from data_types import Data, DataLabel, is_data_label, is_data
from device.name import DeviceName, is_device_name
from experiment.configuration import ExperimentConfig
from parameter_types import Parameter, is_parameter
from sql_model.model import (
    ExperimentConfigModel,
    CurrentExperimentConfigModel,
)
from variable.name import DottedVariableName
from .experiment_session import (
    ExperimentSession,
    ExperimentSessionNotActiveError,
)
from .sql_sequence_hierarchy import SQLSequenceHierarchy
from .sql_shot_collection import SQLShotCollection


@define(init=False)
class SQLExperimentSession(ExperimentSession):
    shot_collection: SQLShotCollection
    sequence_hierarchy: SQLSequenceHierarchy

    _sql_session: sqlalchemy.orm.Session
    _is_active: bool
    _lock: Lock

    def __init__(self, session: sqlalchemy.orm.Session, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sql_session = session
        self._is_active = False
        self._lock = Lock()
        self.shot_collection = SQLShotCollection(parent_session=self)
        self.sequence_hierarchy = SQLSequenceHierarchy(parent_session=self)

    def __enter__(self):
        with self._lock:
            if self._is_active:
                raise RuntimeError("Session is already active")
            self._transaction = self._sql_session.begin().__enter__()
            self._is_active = True
            return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        with self._lock:
            self._transaction.__exit__(exc_type, exc_val, exc_tb)
            self._transaction = None
            self._is_active = False

    # Experiment config methods
    def get_experiment_config(self, name: str) -> ExperimentConfig:
        return ExperimentConfig.from_yaml(
            ExperimentConfigModel.get_config(name, self._get_sql_session())
        )

    def get_all_experiment_config_names(self) -> set[str]:
        session = self._get_sql_session()
        query_names = session.query(ExperimentConfigModel.name)
        names = {name for name in session.scalars(query_names)}
        return names

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
        if not self._is_active:
            raise ExperimentSessionNotActiveError(
                "Experiment session was not activated"
            )
        return self._sql_session


def transform_parameters(
    parameters: Mapping[DottedVariableName, Parameter]
) -> dict[str, Parameter]:
    result = {}
    for dotted_name, parameter in parameters.items():
        if not isinstance(dotted_name, DottedVariableName):
            raise TypeError(
                "Expected instance of <DottedVariableName> for parameter name, got"
                f" {type(dotted_name)}"
            )
        if not is_parameter(parameter):
            raise TypeError(
                f"Expected instance of <Parameter> for parameter '{dotted_name}', got"
                f" {type(parameter)}"
            )
        result[str(dotted_name)] = parameter
    return result


def transform_measures(
    measures: Mapping[DeviceName, Mapping[DataLabel, Data]]
) -> dict[DeviceName, dict[DataLabel, Data]]:
    result = {}
    for device_name, data_group in measures.items():
        if not is_device_name(device_name):
            raise TypeError(
                "Expected instance of <DeviceName> for device name, got"
                f" {type(device_name)}"
            )
        new_group = {}
        for label, data in data_group.items():
            if not is_data_label(label):
                raise TypeError(
                    "Expected instance of <DataLabel> for data label, got"
                    f" {type(label)}"
                )
            if not is_data(data):
                raise TypeError(
                    f"Expected instance of <Data> for device '{device_name}', got"
                    f" {type(data)}"
                )
            new_group[DataLabel(label)] = data
        result[DeviceName(device_name)] = new_group
    return result
