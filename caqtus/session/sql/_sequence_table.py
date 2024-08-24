from __future__ import annotations

import datetime
import enum
from typing import Optional

import sqlalchemy
from sqlalchemy import ForeignKey, DateTime, UniqueConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ._path_table import SQLSequencePath
from ._shot_tables import SQLShot
from ._table_base import Base
from .._state import State


class SQLSequence(Base):
    """This table stores the sequences that are created by the user.

    Attributes:
        id_: The unique identifier of the sequence.
        path_id: The identifier of the path that the sequence is associated with.
        path: A reference to the path that the sequence is associated with.
        state: The state of the sequence.
        parameters: A reference to the parameters of the sequence.
        iteration: A reference to the iteration configuration of the sequence.
        time_lanes: A reference to the time lanes of the sequence.
        device_configurations: A reference to the device configurations of the sequence.
        exceptions: A reference to the exceptions that occurred during the execution of
            the sequence.

            This list of exceptions is non-empty only if the sequence is in the
            "CRASHED" state.

            There can be multiple exceptions if they have different types.

            If the sequence is in the "CRASHED" state, then the list of exceptions
            should at least contain one exception.
            However, for versions <6.3.0, the exceptions were not stored in the database
            and the list of exceptions can be empty even in the "CRASHED" state.

        start_time: The time at which the sequence started execution.

            Stored as a timezone naive datetime, with the assumption that the timezone
            is UTC.

        stop_time: The time at which the sequence stopped execution.

            Stored as a timezone naive datetime, with the assumption that the timezone
            is UTC.

        shots: A reference to the shots that are part of the sequence.
        expected_number_of_shots: The number of shots that are expected to be executed
            in total for this sequence, inferred from the iteration configuration.

            Can be None if this value is not known.
    """

    __tablename__ = "sequences"

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    path_id: Mapped[str] = mapped_column(
        ForeignKey(SQLSequencePath.id_, ondelete="CASCADE"), unique=True, index=True
    )
    path: Mapped[SQLSequencePath] = relationship(back_populates="sequence")
    state: Mapped[State]

    parameters: Mapped[SQLSequenceParameters] = relationship(
        cascade="all, delete",
        passive_deletes=True,
        back_populates="sequence",
    )
    iteration: Mapped[SQLIterationConfiguration] = relationship(
        cascade="all",
        passive_deletes=True,
        back_populates="sequence",
    )
    time_lanes: Mapped[SQLTimelanes] = relationship(
        cascade="all, delete",
        passive_deletes=True,
        back_populates="sequence",
    )

    device_configurations: Mapped[list[SQLDeviceConfiguration]] = relationship(
        cascade="all, delete", passive_deletes=True, back_populates="sequence"
    )

    exceptions: Mapped[list[SequenceException]] = relationship(
        cascade="all, delete", passive_deletes=True, back_populates="sequence"
    )

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


class SQLSequenceParameters(Base):
    __tablename__ = "sequence.parameters"

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    sequence_id: Mapped[int] = mapped_column(
        ForeignKey(SQLSequence.id_, ondelete="CASCADE"), index=True
    )
    sequence: Mapped[SQLSequence] = relationship(
        back_populates="parameters", single_parent=True
    )
    content = mapped_column(sqlalchemy.types.JSON)

    __table_args__ = (UniqueConstraint(sequence_id),)


class SQLIterationConfiguration(Base):
    __tablename__ = "sequence.iteration"

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    sequence_id: Mapped[int] = mapped_column(
        ForeignKey(SQLSequence.id_, ondelete="CASCADE"), index=True
    )
    sequence: Mapped[SQLSequence] = relationship(
        back_populates="iteration", single_parent=True
    )
    content = mapped_column(sqlalchemy.types.JSON)

    __table_args__ = (UniqueConstraint(sequence_id),)


class SQLTimelanes(Base):
    __tablename__ = "sequence.time_lanes"

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    sequence_id: Mapped[int] = mapped_column(
        ForeignKey(SQLSequence.id_, ondelete="CASCADE"), index=True
    )
    sequence: Mapped[SQLSequence] = relationship(
        back_populates="time_lanes", single_parent=True
    )
    content = mapped_column(sqlalchemy.types.JSON)

    __table_args__ = (UniqueConstraint(sequence_id),)


class SQLDeviceConfiguration(Base):
    __tablename__ = "sequence.device_configurations"

    id_: Mapped[int] = mapped_column(primary_key=True)
    sequence_id: Mapped[int] = mapped_column(
        ForeignKey(SQLSequence.id_, ondelete="CASCADE")
    )
    sequence: Mapped[SQLSequence] = relationship(back_populates="device_configurations")
    name: Mapped[str] = mapped_column(String(255))
    device_type: Mapped[str] = mapped_column(String(255))
    content = mapped_column(sqlalchemy.types.JSON)

    __table_args__ = (
        sqlalchemy.UniqueConstraint(sequence_id, name, name="device_configuration"),
    )


class ExceptionType(enum.IntEnum):
    """Tag for the type of exception that occurred.

    Attributes:
        SYSTEM: Indicates an exception that occurred due to a programming error.
        USER: Indicates an exception that occurred due to user input.
    """

    SYSTEM = 0
    USER = 1


class SequenceException(Base):
    """This table stores exceptions that occur during the execution of sequences.

    For a given sequence, there can be multiple exceptions with different types, but
    only one of a given type.

    Attributes:
        id_: The unique identifier of the exception.
        sequence_id: The identifier of the sequence that the exception occurred in.
        sequence: The sequence that the exception occurred in.
        type_: The type of exception that occurred.
        content: The content of the exception in JSON format.
    """

    __tablename__ = "sequence.exceptions"

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    sequence_id: Mapped[int] = mapped_column(
        ForeignKey(SQLSequence.id_, ondelete="CASCADE"), index=True
    )
    sequence: Mapped[SQLSequence] = relationship(back_populates="exceptions")
    type_: Mapped[ExceptionType] = mapped_column(name="type", nullable=False)
    content = mapped_column(sqlalchemy.types.JSON)

    __table_args__ = (
        sqlalchemy.UniqueConstraint(sequence_id, type_, name="exception"),
    )
