from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

import attrs
import sqlalchemy
from sqlalchemy.orm import Mapped, mapped_column

from ._table_base import Base
from .device_configuration_serializer import DeviceConfigurationSerializer
from ..device_configuration_collection import DeviceConfigurationCollection

if TYPE_CHECKING:
    from ._experiment_session import SQLExperimentSession


class SQLDefaultDeviceConfiguration(Base):
    __tablename__ = "default_device_configurations"

    name: Mapped[str] = mapped_column(primary_key=True)
    device_type: Mapped[str] = mapped_column()
    content = mapped_column(sqlalchemy.types.JSON)


@attrs.frozen
class SQLDeviceConfigurationCollection(DeviceConfigurationCollection):
    parent_session: "SQLExperimentSession"
    device_configuration_serializers: Mapping[str, DeviceConfigurationSerializer]

    def __setitem__(self, __key, __value):
        pass

    def __delitem__(self, __key):
        pass

    def __getitem__(self, __key):
        pass

    def __len__(self):
        pass

    def __iter__(self):
        pass
