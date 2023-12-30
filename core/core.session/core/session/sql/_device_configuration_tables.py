import datetime
import uuid

import sqlalchemy
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ._table_base import Base


class SQLDeviceConfiguration(Base):
    __tablename__ = "device_configurations"

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "device_name", "creation_date", name="configuration_identifier"
        ),
    )

    uuid = mapped_column(sqlalchemy.types.Uuid, primary_key=True)
    device_name: Mapped[str] = mapped_column()
    module: Mapped[str] = mapped_column()
    type: Mapped[str] = mapped_column()
    content = mapped_column(sqlalchemy.types.JSON)
    creation_date: Mapped[datetime.datetime] = mapped_column()


class SQLCurrentDeviceConfiguration(Base):
    __tablename__ = "device_configurations_in_use"

    id_: Mapped[int] = mapped_column(primary_key=True)
    in_use: Mapped[uuid.UUID] = mapped_column(
        sqlalchemy.ForeignKey(SQLDeviceConfiguration.uuid)
    )
    configuration: Mapped[SQLDeviceConfiguration] = relationship()
