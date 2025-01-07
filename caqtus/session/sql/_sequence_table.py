from __future__ import annotations

import datetime
from typing import Optional

import sqlalchemy
from sqlalchemy import ForeignKey, DateTime, UniqueConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from caqtus.utils.serialization import JsonDict
from ._path_table import SQLSequencePath
from ._shot_tables import SQLShot, SQLShotData
from ._table_base import Base
from .._state import State


class SQLSequence(Base):
    """This table stores the sequences that are created by the user.

    Attributes:
        id_: The unique identifier of the sequence.
        path_id: The identifier of the path that the sequence is associated with.
        path: A reference to the path that the sequence is associated with.
        state: The state of the sequence.
        parameter_schema: A reference to the schema of the parameters of the sequence.
            This is None if the sequence is in the DRAFT or PREPARING state and is set
            when the sequence is RUNNING, INTERRUPTED or FINISHED.
            If the sequence is CRASHED, the schema will be None is the sequence crashed
            before the schema was set.
        exception_traceback: The traceback of the exception that occurred while running
            the sequence.

            This is None if the sequence is not in the CRASHED state.

            It can be None even if the sequence is in the CRASHED state if the traceback
            was not captured.

        parameters: A reference to the global parameters of the sequence at the time it
            was launched.
            It is None if the sequence is in the DRAFT state and is set when the
            sequence is prepared.
        iteration: A reference to the iteration configuration of the sequence.
        time_lanes: A reference to the time lanes of the sequence.
        device_configurations: A reference to the device configurations of the sequence.

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
    exception_traceback: Mapped[Optional[SQLExceptionTraceback]] = relationship(
        cascade="all, delete", passive_deletes=True, back_populates="sequence"
    )
    parameter_schema: Mapped[Optional[SQLParameterSchema]] = relationship(
        cascade="all, delete",
        passive_deletes=True,
        back_populates="sequence",
    )

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
    __tablename__ = "device_config"

    id_: Mapped[int] = mapped_column(primary_key=True)
    sequence_id: Mapped[int] = mapped_column(
        ForeignKey(SQLSequence.id_, ondelete="CASCADE")
    )
    sequence: Mapped[SQLSequence] = relationship(back_populates="device_configurations")
    name: Mapped[str] = mapped_column(String(255))
    device_type: Mapped[str] = mapped_column(String(255))
    content = mapped_column(sqlalchemy.types.JSON)
    device_server: Mapped[Optional[str]] = mapped_column()
    data_schemas: Mapped[list[SQLDataSchema]] = relationship(
        cascade="all, delete",
        passive_deletes=True,
        back_populates="device_configuration",
    )

    __table_args__ = (
        sqlalchemy.UniqueConstraint(sequence_id, name, name="device_configuration"),
    )


class SQLDataSchema(Base):
    """Contains the schema for the data of a sequence.

    Attributes:
        id_: The unique identifier of the data schema.
        device_configuration_id: The identifier of the device configuration that is
            associated with the data.
        label: The label of the schema.
            For a given device configuration, the label must be unique.
        data_type: The data type of the schema.
            This is a JSON object that describes the data type of the schema.
            The object maps the name of the data type to a JSON object that describes
            the data type, like so: {"Array": {"dtype": "float64", "shape": [2, 3]}}
        retention_policy: The retention policy of the data.
            Indicates if the data should be saved or not during the sequence, and for
            how long it should be saved.
    """

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    device_configuration_id: Mapped[int] = mapped_column(
        ForeignKey(SQLDeviceConfiguration.id_, ondelete="CASCADE"),
        index=True,
    )
    device_configuration: Mapped[SQLDeviceConfiguration] = relationship(
        back_populates="data_schemas"
    )
    label: Mapped[str] = mapped_column()
    data_type: Mapped[JsonDict] = mapped_column()
    data: Mapped[list[SQLShotData]] = relationship(
        cascade="all, delete",
        passive_deletes=True,
        back_populates="schema",
    )
    retention_policy: Mapped[JsonDict] = mapped_column()

    __tablename__ = "data_schema"
    __table_args__ = (UniqueConstraint(device_configuration_id, label),)


class SQLParameterSchema(Base):
    """Contains the schema for the parameters of a sequence.

    Attributes:
        id_: The unique identifier of the parameter schema.
        sequence_id: The identifier of the sequence that is associated with the schema.
        sequence: A reference to the sequence that is associated with the schema.
        parameter_name: The name of the parameter.
            For a given sequence, the parameter name must be unique.
        parameter_type: The content of the schema.
            This is a JSON object that describes an object of type `ParameterSchema`
            that defines the type of the parameters in the sequence.
    """

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    sequence_id: Mapped[int] = mapped_column(
        ForeignKey(SQLSequence.id_, ondelete="CASCADE"), index=True
    )
    sequence: Mapped[SQLSequence] = relationship(
        back_populates="parameter_schema", single_parent=True
    )
    parameter_name: Mapped[str] = mapped_column()
    parameter_type: Mapped[JsonDict] = mapped_column()

    __tablename__ = "parameter_schema"
    __table_args__ = (UniqueConstraint(sequence_id, parameter_name),)


class SQLExceptionTraceback(Base):
    __tablename__ = "sequence.exception_tracebacks"

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    sequence_id: Mapped[int] = mapped_column(
        ForeignKey(SQLSequence.id_, ondelete="CASCADE"), index=True
    )
    sequence: Mapped[SQLSequence] = relationship(
        back_populates="exception_traceback", single_parent=True
    )
    content = mapped_column(sqlalchemy.types.JSON, nullable=False)

    __table_args__ = (UniqueConstraint(sequence_id),)
