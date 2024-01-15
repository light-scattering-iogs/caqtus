import datetime
from typing import TYPE_CHECKING

from sqlalchemy import UniqueConstraint, ForeignKey, JSON
from sqlalchemy.orm import mapped_column, Mapped, relationship

from ._table_base import Base

if TYPE_CHECKING:
    from ._sequence_table import SQLSequence


class SQLShot(Base):
    __tablename__ = "shots"

    __table_args__ = (UniqueConstraint("sequence_id", "index", name="shot_identifier"),)

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    sequence_id: Mapped[int] = mapped_column(ForeignKey("sequences.id"), index=True)
    sequence: Mapped["SQLSequence"] = relationship(back_populates="shots")
    index: Mapped[int] = mapped_column(index=True)

    start_time: Mapped[datetime.datetime] = mapped_column()
    end_time: Mapped[datetime.datetime] = mapped_column()

    parameters: Mapped[list["SQLShotParameter"]] = relationship(
        cascade="all, delete, delete-orphan", passive_deletes=True
    )


class SQLShotParameter(Base):
    __tablename__ = "shot_parameters"

    __table_args__ = (UniqueConstraint("shot_id", "name", name="parameter_identifier"),)

    id_: Mapped[int] = mapped_column(primary_key=True)
    shot_id: Mapped[int] = mapped_column(ForeignKey("shots.id"), index=True)
    name: Mapped[str] = mapped_column()
    value = mapped_column(JSON)
