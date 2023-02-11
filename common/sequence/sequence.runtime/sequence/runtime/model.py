from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .state import State


class SequenceModel(Base):
    __tablename__ = "sequence"

    path: Mapped[str] = mapped_column(primary_key=True)
    state: Mapped[State]

    sequence_config_yaml: Mapped[str] = mapped_column()
    experiment_config_yaml: Mapped[Optional[str]] = mapped_column()

    creation_date: Mapped[datetime] = mapped_column()
    modification_date: Mapped[datetime] = mapped_column()
    start_date: Mapped[Optional[datetime]] = mapped_column()
    stop_date: Mapped[Optional[datetime]] = mapped_column()

    def __repr__(self):
        return (
            f"SequenceModel(path={self.path}, state={self.state},"
            f" creation_date={self.creation_date},"
            f" modification_date={self.modification_date},"
            f" start_date={self.start_date}, stop_date={self.stop_date})"
        )
