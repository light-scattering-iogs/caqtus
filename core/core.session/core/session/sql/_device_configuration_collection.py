import datetime
import uuid
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, TypedDict

import attrs
import sqlalchemy
from core.device import (
    DeviceName,
    DeviceConfigurationAttrs,
)
from util.serialization import JSON
from ._device_configuration_tables import (
    SQLDeviceConfiguration,
    SQLCurrentDeviceConfiguration,
)
from ..device_configuration_collection import DeviceConfigurationCollection

if TYPE_CHECKING:
    from ._experiment_session import SQLExperimentSession


class DeviceConfigurationSerializer[T: DeviceConfigurationAttrs](TypedDict):
    dumper: Callable[[T], JSON]
    loader: Callable[[JSON], T]


@attrs.frozen
class SQLDeviceConfigurationCollection(
    DeviceConfigurationCollection,
):
    parent_session: "SQLExperimentSession"

    _device_configuration_serializers: Mapping[str, DeviceConfigurationSerializer]

    def add_device_configuration(
        self,
        device_name: DeviceName,
        device_configuration: DeviceConfigurationAttrs,
    ) -> uuid.UUID:
        creation_date = datetime.datetime.now(tz=datetime.timezone.utc)
        id_ = self._create_uuid(device_name, creation_date)
        type_name = type(device_configuration).__qualname__
        serializer = self._device_configuration_serializers[type_name]
        new = SQLDeviceConfiguration(
            uuid=id_,
            device_name=device_name,
            device_type=type_name,
            content=serializer["dumper"](device_configuration),
            creation_date=creation_date,
        )
        self._get_sql_session().add(new)
        return id_

    def get_device_name(self, id_: uuid.UUID) -> DeviceName:
        return self._get_configuration(id_).device_name

    def get_configuration(self, id_: uuid.UUID) -> DeviceConfigurationAttrs:
        configuration = self._get_configuration(id_)
        serializer = self._device_configuration_serializers[configuration.device_type]
        return serializer["loader"](configuration.content)

    def set_in_use(self, id_: uuid.UUID) -> None:
        new = SQLCurrentDeviceConfiguration(
            in_use=id_,
            device_name=self.get_device_name(id_),
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
