from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Mapped, mapped_column, Session

from experiment_config import ExperimentConfig
from sequence.configuration import SequenceConfig
from . import SequencePath
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

    @classmethod
    def create_sequence(
        cls,
        path: SequencePath,
        sequence_config: SequenceConfig,
        experiment_config: Optional[ExperimentConfig],
        session: Session,
    ):
        path_ancestors = [
            str(ancestor) for ancestor in path.get_ancestors(strict=False)
        ]
        query = select(SequenceModel).filter(SequenceModel.path.in_(path_ancestors))
        sequence_ancestors = session.scalars(query).all()

        if sequence_ancestors:
            raise RuntimeError(
                f"Cannot create sequence {path} because a sequence already exists in"
                f" this path {sequence_ancestors}"
            )

        query = select(SequenceModel).filter(SequenceModel.path.startswith(str(path)))
        sequence_descendants = session.scalars(query).all()

        if sequence_descendants:
            raise RuntimeError(
                f"Cannot create sequence {path} because a sequence already exists in"
                f" this path {sequence_descendants}"
            )

        now = datetime.now()
        creation_args = {
            "path": str(path),
            "state": State.DRAFT,
            "sequence_config_yaml": sequence_config.to_yaml(),
            "experiment_config_yaml": experiment_config.to_yaml()
            if experiment_config
            else None,
            "creation_date": now,
            "modification_date": now,
            "start_date": None,
            "stop_date": None,
        }

        sequence_sql = SequenceModel(**creation_args)
        session.add(sequence_sql)
