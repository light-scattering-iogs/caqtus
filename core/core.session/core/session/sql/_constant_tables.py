import datetime
import uuid

import sqlalchemy
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ._table_base import Base


class SQLConstantDeclaration(Base):
    __tablename__ = "constant_declarations"

    id_: Mapped[int] = mapped_column(primary_key=True)
    variable: Mapped[str] = mapped_column()
    expression: Mapped[str] = mapped_column()
    table_uuid: Mapped[uuid.UUID] = mapped_column(
        sqlalchemy.ForeignKey("constant_tables.uuid")
    )
    table: Mapped["SQLConstantTable"] = relationship()


class SQLConstantTable(Base):
    __tablename__ = "constant_tables"

    __table_args__ = (
        sqlalchemy.UniqueConstraint("name", "creation_date", name="table_identifier"),
    )

    uuid = mapped_column(sqlalchemy.types.Uuid, primary_key=True)
    name: Mapped[str] = mapped_column()
    creation_date: Mapped[datetime.datetime] = mapped_column()
    constant_declarations: Mapped[list[SQLConstantDeclaration]] = relationship()


class SQLCurrentConstantTables(Base):
    __tablename__ = "constant_tables_in_use"

    id_: Mapped[int] = mapped_column(primary_key=True)
    in_use: Mapped[uuid.UUID] = mapped_column(
        sqlalchemy.ForeignKey(SQLConstantTable.uuid)
    )
    table_name: Mapped[str] = mapped_column(unique=True, index=True)
    table: Mapped[SQLConstantTable] = relationship()
