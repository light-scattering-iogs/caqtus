import datetime
import importlib
import uuid
from typing import TYPE_CHECKING

import attrs
import sqlalchemy

from core.device import (
    DeviceName,
    DeviceConfigurationAttrs,
    device_configurations_converter,
)
from ._device_configuration_tables import (
    SQLDeviceConfiguration,
    SQLCurrentDeviceConfiguration,
)
from ..device_configuration_collection import DeviceConfigurationCollection

if TYPE_CHECKING:
    from ._experiment_session import SQLExperimentSession


@attrs.frozen
class SQLDeviceConfigurationCollection(
    DeviceConfigurationCollection,
):
    parent_session: "SQLExperimentSession"

    def add_device_configuration(
        self,
        device_name: DeviceName,
        device_configuration: DeviceConfigurationAttrs,
    ) -> uuid.UUID:
        creation_date = datetime.datetime.now(tz=datetime.timezone.utc)
        id_ = self._create_uuid(device_name, creation_date)
        cls = device_configuration.__class__
        new = SQLDeviceConfiguration(
            uuid=id_,
            device_name=device_name,
            module=cls.__module__,
            type=cls.__qualname__,
            content=device_configurations_converter.unstructure(device_configuration),
            creation_date=creation_date,
        )
        self._get_sql_session().add(new)
        return id_

    def get_device_name(self, id_: uuid.UUID) -> DeviceName:
        return self._get_configuration(id_).device_name

    def get_configuration(self, id_: uuid.UUID) -> DeviceConfigurationAttrs:
        configuration = self._get_configuration(id_)
        module = importlib.import_module(configuration.module)
        cls = getattr(module, configuration.type)
        return device_configurations_converter.structure(configuration.content, cls)

    def set_in_use(self, id_: uuid.UUID) -> None:
        new = SQLCurrentDeviceConfiguration(
            in_use=id_,
        )
        self._get_sql_session().add(new)

    def remove_from_use(self, id_: uuid.UUID):
        action = sqlalchemy.delete(SQLCurrentDeviceConfiguration).where(
            SQLCurrentDeviceConfiguration.in_use == id_
        )
        self._get_sql_session().execute(action)

    def get_in_use_uuids(self) -> set[uuid.UUID]:
        query = sqlalchemy.select(SQLCurrentDeviceConfiguration.in_use)
        return {id_ for id_, in self._get_sql_session().execute(query)}

    def _get_configuration(self, id_: uuid.UUID) -> SQLDeviceConfiguration:
        query = sqlalchemy.select(SQLDeviceConfiguration).where(
            SQLDeviceConfiguration.uuid == id_
        )
        return self._get_sql_session().execute(query).scalar_one()

    def _get_sql_session(self) -> sqlalchemy.orm.Session:
        # noinspection PyProtectedMember
        return self.parent_session._get_sql_session()
