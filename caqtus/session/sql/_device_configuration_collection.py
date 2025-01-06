from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import attrs
import sqlalchemy
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, Session

from ._serializer import SerializerProtocol
from ._table_base import Base
from .._device_configuration_collection import DeviceConfigurationCollection
from ...device import DeviceName
from ...device.configuration import DeviceServerName

if TYPE_CHECKING:
    from ._experiment_session import SQLExperimentSession


class SQLDefaultDeviceConfiguration(Base):
    """Table for storing device configurations to use by default."""

    __tablename__ = "default_device_configurations"

    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    device_type: Mapped[str] = mapped_column(String(255))
    content = mapped_column(sqlalchemy.types.JSON)
    device_server: Mapped[Optional[str]] = mapped_column(nullable=True)


@attrs.frozen
class SQLDeviceConfigurationCollection(DeviceConfigurationCollection):
    parent_session: "SQLExperimentSession"
    serializer: SerializerProtocol

    def __setitem__(self, __key, __value):
        type_name, content = self.serializer.dump_device_configuration(__value)
        if __key in self:
            stmt = (
                sqlalchemy.update(SQLDefaultDeviceConfiguration)
                .where(SQLDefaultDeviceConfiguration.name == str(__key))
                .values(content=content)
            )
        else:
            stmt = sqlalchemy.insert(SQLDefaultDeviceConfiguration).values(
                name=str(__key), device_type=type_name, content=content
            )
        self._get_sql_session().execute(stmt)

    def __delitem__(self, __key):
        if __key not in self:
            raise KeyError(__key)
        stmt = sqlalchemy.delete(SQLDefaultDeviceConfiguration).where(
            SQLDefaultDeviceConfiguration.name == str(__key)
        )
        self._get_sql_session().execute(stmt)

    def __getitem__(self, __key):
        item = self._get_item(__key)
        if item is None:
            raise KeyError(__key)
        else:
            device_config = self.serializer.load_device_configuration(
                item.device_type, item.content
            )
            return device_config

    def get_device_server(self, device_name: DeviceName) -> Optional[DeviceServerName]:
        item = self._get_item(device_name)
        if item is None:
            raise KeyError(device_name)
        return (
            DeviceServerName(item.device_server)
            if item.device_server is not None
            else None
        )

    def set_device_server(
        self, device_name: DeviceName, server_name: Optional[DeviceServerName]
    ) -> None:
        item = self._get_item(device_name)
        if item is None:
            raise KeyError(device_name)
        item.device_server = server_name
        self._get_sql_session().flush([item])

    def _get_item(
        self, device_name: DeviceName
    ) -> Optional[SQLDefaultDeviceConfiguration]:
        stmt = sqlalchemy.select(SQLDefaultDeviceConfiguration).where(
            SQLDefaultDeviceConfiguration.name == str(device_name)
        )
        result = self._get_sql_session().execute(stmt)
        return result.scalar()

    def __len__(self):
        stmt = sqlalchemy.select(
            sqlalchemy.func.count(SQLDefaultDeviceConfiguration.name)
        )
        result = self._get_sql_session().execute(stmt).scalar()
        assert isinstance(result, int)
        return result

    def __iter__(self):
        stmt = sqlalchemy.select(SQLDefaultDeviceConfiguration).order_by(
            SQLDefaultDeviceConfiguration.name
        )
        result = self._get_sql_session().execute(stmt)
        return (DeviceName(row.name) for row in result.scalars())

    def __contains__(self, item):
        stmt = sqlalchemy.select(
            sqlalchemy.func.count(SQLDefaultDeviceConfiguration.name)
        ).where(SQLDefaultDeviceConfiguration.name == str(item))
        result = self._get_sql_session().execute(stmt).scalar()
        assert isinstance(result, int)
        return result > 0

    def _get_sql_session(self) -> Session:
        # noinspection PyProtectedMember
        return self.parent_session._get_sql_session()
