from __future__ import annotations

import datetime
from typing import Optional

import sqlalchemy
from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ._path_table import SQLSequencePath
from ._shot_tables import SQLShot
from ._table_base import Base
from ..sequence.state import State


class SQLIterationConfiguration(Base):
    __tablename__ = "sequence.iteration"

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    sequence_id: Mapped[int] = mapped_column(
        ForeignKey("sequences.id", ondelete="CASCADE"), index=True, unique=True
    )
    sequence: Mapped["SQLSequence"] = relationship(back_populates="iteration")
    content = mapped_column(sqlalchemy.types.JSON)


class SQLTimelanes(Base):
    __tablename__ = "sequence.timelanes"

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    sequence_id: Mapped[int] = mapped_column(
        ForeignKey("sequences.id", ondelete="CASCADE"), index=True, unique=True
    )
    sequence: Mapped["SQLSequence"] = relationship(back_populates="time_lanes")
    content = mapped_column(sqlalchemy.types.JSON)


class SQLSequence(Base):
    __tablename__ = "sequences"

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    path_id: Mapped[str] = mapped_column(
        ForeignKey(SQLSequencePath.id_, ondelete="CASCADE"), unique=True, index=True
    )
    path: Mapped[SQLSequencePath] = relationship(back_populates="sequence")
    state: Mapped[State]

    iteration: Mapped[SQLIterationConfiguration] = relationship(cascade="all")
    time_lanes: Mapped[SQLTimelanes] = relationship(
        cascade="all, delete", back_populates="sequence", passive_deletes=True
    )
    device_configurations: Mapped[list[SQLDeviceConfiguration]] = relationship(
        cascade="all, delete", passive_deletes=True
    )
    parameters = mapped_column(sqlalchemy.types.JSON)

    # Stored as timezone naive datetimes, with the assumption that the timezone is UTC.
    start_time: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=False)
    )
    stop_time: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=False)
    )

    shots: Mapped[list["SQLShot"]] = relationship(
        back_populates="sequence",
        cascade="all, delete",
        passive_deletes=True,
    )
    # expected_number_of_shots indicates how many shots are expected to be executed in
    # total for this sequence.
    # It is written when the sequence iteration is set.
    # None indicates that this value is not known.
    expected_number_of_shots: Mapped[Optional[int]] = mapped_column()


class SQLDeviceConfiguration(Base):
    __tablename__ = "sequence.device_configurations"

    # For a given sequence, the device configuration name must be unique.
    __table_args__ = (
        sqlalchemy.UniqueConstraint("sequence_id", "name", name="device_configuration"),
    )

    id_: Mapped[int] = mapped_column(primary_key=True)
    sequence_id: Mapped[int] = mapped_column(
        ForeignKey(SQLSequence.id_, ondelete="CASCADE")
    )
    sequence: Mapped[SQLSequence] = relationship(back_populates="device_configurations")
    name: Mapped[str] = mapped_column()
    device_type: Mapped[str] = mapped_column()
    order: Mapped[int] = mapped_column()
    content = mapped_column(sqlalchemy.types.JSON)
