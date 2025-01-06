import datetime
from typing import TYPE_CHECKING

from sqlalchemy import UniqueConstraint, ForeignKey, JSON, LargeBinary, DateTime, String
from sqlalchemy.orm import mapped_column, Mapped, relationship

from ._table_base import Base

if TYPE_CHECKING:
    from ._sequence_table import SQLSequence, SQLDataSchema


class SQLShot(Base):
    __tablename__ = "shots"

    __table_args__ = (UniqueConstraint("sequence_id", "index", name="shot_identifier"),)

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    sequence_id: Mapped[int] = mapped_column(
        ForeignKey("sequences.id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped["SQLSequence"] = relationship(back_populates="shots")
    index: Mapped[int] = mapped_column(index=True)

    # Stored without explicit timezone, with the assumption that all times are UTC.
    start_time: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=False))
    end_time: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=False))

    parameters: Mapped["SQLShotParameter"] = relationship(
        back_populates="shot",
        cascade="all, delete",
        passive_deletes=True,
    )
    data: Mapped[list["SQLShotData"]] = relationship(
        back_populates="shot",
        cascade="all, delete",
        passive_deletes=True,
    )
    array_data: Mapped[list["SQLShotArray"]] = relationship(
        back_populates="shot",
        cascade="all, delete",
        passive_deletes=True,
    )
    structured_data: Mapped[list["SQLStructuredShotData"]] = relationship(
        back_populates="shot",
        cascade="all, delete",
        passive_deletes=True,
    )


# Shot parameters are stored as a single JSON row per shot, which is a dictionary
# mapping parameter names to values.
# Since we usually load all parameters at once, there is not much need to have a row for
# each single parameter.
class SQLShotParameter(Base):
    __tablename__ = "shot.parameters"

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    shot_id: Mapped[int] = mapped_column(
        ForeignKey("shots.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    shot: Mapped[SQLShot] = relationship(back_populates="parameters")
    content = mapped_column(JSON)


class SQLShotData(Base):
    """Table for storing data for each shot.

    Attributes:
        id_: Primary key of the table.
        shot_id: Foreign key to the shot.
        shot: Relationship to the shot.
        schema_id: Foreign key to the data schema.
        schema: Relationship to the data schema.
        content: The data content.
            This is stored as bytes.
            The conversion to and from the actual data type is done by the data schema.
    """

    __tablename__ = "shot.data"

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    shot_id: Mapped[int] = mapped_column(
        ForeignKey(SQLShot.id_, ondelete="CASCADE"),
        index=True,
    )
    shot: Mapped[SQLShot] = relationship(back_populates="data")
    schema_id: Mapped[int] = mapped_column(
        ForeignKey("sequence.data_schema.id", ondelete="CASCADE"),
        index=True,
    )
    schema: Mapped["SQLDataSchema"] = relationship(back_populates="data")
    content: Mapped[bytes] = mapped_column()

    __table_args__ = (UniqueConstraint(shot_id, schema_id),)


# Unlike parameters, data are stored as many rows per shot. This is because we might not
# need to load all data for each shot every time.
# Data are separated in two sub-tables: one for structured nested data that contains
# few elements, and one for large arrays of bytes.
class SQLStructuredShotData(Base):
    __tablename__ = "shot.data.structured"

    __table_args__ = (
        UniqueConstraint("shot_id", "label", name="structured_identifier"),
    )

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    shot_id: Mapped[int] = mapped_column(
        ForeignKey("shots.id", ondelete="CASCADE"),
        index=True,
    )
    shot: Mapped[SQLShot] = relationship(back_populates="structured_data")
    label: Mapped[str] = mapped_column(String(255))
    content = mapped_column(JSON)


class SQLShotArray(Base):
    __tablename__ = "shot.data.arrays"

    __table_args__ = (UniqueConstraint("shot_id", "label", name="array_identifier"),)

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    shot_id: Mapped[int] = mapped_column(
        ForeignKey("shots.id", ondelete="CASCADE"),
        index=True,
    )
    shot: Mapped[SQLShot] = relationship(back_populates="array_data")
    label: Mapped[str] = mapped_column(String(255))
    dtype: Mapped[str] = mapped_column(String(255))
    shape = mapped_column(JSON)
    bytes_ = mapped_column(LargeBinary, name="bytes")  # stored in C-order
