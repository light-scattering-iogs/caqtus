from __future__ import annotations

import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ._table_base import Base

if TYPE_CHECKING:
    from ._sequence_table import SQLSequence


class SQLSequencePath(Base):
    __tablename__ = "path"

    id_: Mapped[int] = mapped_column(name="id", primary_key=True, index=True)
    path: Mapped[str] = mapped_column(index=True, unique=True)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("path.id"), index=True)

    children: Mapped[list[SQLSequencePath]] = relationship(
        back_populates="parent", cascade="delete, delete-orphan"
    )
    parent: Mapped[SQLSequencePath] = relationship(
        back_populates="children", remote_side=[id_]
    )
    creation_date: Mapped[datetime.datetime] = mapped_column()
    sequence: Mapped[Optional["SQLSequence"]] = relationship(
        back_populates="path", cascade="delete, delete-orphan"
    )

    def __str__(self):
        return str(self.path)
