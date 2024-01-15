import datetime
from typing import TYPE_CHECKING

from sqlalchemy import UniqueConstraint, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from ._table_base import Base

if TYPE_CHECKING:
    from ._sequence_table import SQLSequence


class SQLShot(Base):
    __tablename__ = "shots"

    __table_args__ = (UniqueConstraint("sequence_id", "index", name="shot_identifier"),)

    id_: Mapped[int] = mapped_column(primary_key=True)
    sequence_id: Mapped[int] = mapped_column(ForeignKey("sequences.id"))
    sequence: Mapped["SQLSequence"] = relationship(back_populates="shots")
    index: Mapped[int] = mapped_column()

    start_time: Mapped[datetime.datetime] = mapped_column()
    end_time: Mapped[datetime.datetime] = mapped_column()
