import enum
import typing
from datetime import datetime
from typing import Optional, Any

from sqlalchemy import (
    select,
    ForeignKey,
    UniqueConstraint,
    PickleType,
    Column,
    func,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, Session, relationship, remote, foreign
from sqlalchemy_utils import Ltree, LtreeType

from experiment_config import ExperimentConfig
from sequence.configuration import SequenceConfig
from .base import Base
from .state import State

if typing.TYPE_CHECKING:
    from .path import SequencePath

# Need to activate Ltree extension in Postgresql
# In the psql shell:
# CREATE EXTENSION IF NOT EXISTS ltree;


class SequencePathModel(Base):
    __tablename__ = "sequence_path"

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    path = Column(LtreeType, unique=True, nullable=False)
    creation_date: Mapped[datetime] = mapped_column()
    parent: Mapped[Optional["SequencePathModel"]] = relationship(
        primaryjoin=remote(path) == foreign(func.subpath(path, 0, -1)),
        backref="children",
        viewonly=True,
    )
    sequence: Mapped[
        list["SequenceModel"]
    ] = relationship()  # the list will always contain either 0 or 1 element

    __table_args__ = (Index("ix_nodes_path", path, postgresql_using="gist"),)

    @classmethod
    def create_path(
        cls,
        path: "SequencePath",
        session: Session,
    ):
        session.add(cls(path=Ltree(str(path)), creation_date=datetime.now()))
        session.flush()

    def is_sequence(self) -> bool:
        return len(self.sequence) == 1

    def get_sequence(self) -> "SequenceModel":
        return self.sequence[0]


class SequenceModel(Base):
    __tablename__ = "sequence"

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    path_id: Mapped[str] = mapped_column(
        ForeignKey("sequence_path.id"), unique=True, index=True
    )
    path: Mapped[SequencePathModel] = relationship(back_populates="sequence")
    state: Mapped[State]

    sequence_config_yaml: Mapped[str] = mapped_column()
    experiment_config_yaml: Mapped[Optional[str]] = mapped_column()

    creation_date: Mapped[datetime] = mapped_column()
    modification_date: Mapped[datetime] = mapped_column()
    start_date: Mapped[Optional[datetime]] = mapped_column()
    stop_date: Mapped[Optional[datetime]] = mapped_column()

    total_number_shots: Mapped[Optional[int]] = mapped_column()  # None indicates that this number is unknown
    number_completed_shots: Mapped[int] = mapped_column()

    shots: Mapped[list["ShotModel"]] = relationship()

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
        path: "SequencePath",
        sequence_config: SequenceConfig,
        experiment_config: Optional[ExperimentConfig],
        session: Session,
    ):

        query_path_id = select(SequencePathModel.id_).filter(
            SequencePathModel.path == Ltree(str(path))
        )
        path_id = session.scalar(query_path_id)


        now = datetime.now()
        sequence_sql = SequenceModel(
            path_id=path_id,
            state=State.DRAFT,
            sequence_config_yaml=sequence_config.to_yaml(),
            experiment_config_yaml=experiment_config.to_yaml()
            if experiment_config
            else None,
            creation_date=now,
            modification_date=now,
            start_date=None,
            stop_date=None,
            total_number_shots=sequence_config.compute_total_number_of_shots(),
            number_completed_shots=0
        )
        session.add(sequence_sql)
        session.flush()
        return sequence_sql


class ShotModel(Base):
    __tablename__ = "shot"
    __table_args__ = (
        UniqueConstraint("sequence_id", "name", "index", name="shot_identifier"),
    )

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    sequence_id: Mapped[str] = mapped_column(ForeignKey("sequence.id"), index=True)
    sequence: Mapped["SequenceModel"] = relationship(back_populates="shots")
    name: Mapped[str] = mapped_column()
    index: Mapped[int] = mapped_column()

    start_time: Mapped[datetime] = mapped_column()
    end_time: Mapped[datetime] = mapped_column()

    data: Mapped[list["DataModel"]] = relationship()

    @classmethod
    def create_shot(
        cls,
        sequence: SequenceModel,
        name: str,
        start_time: datetime,
        end_time: datetime,
        session: Session,
    ):
        query_previous_shot = (
            select(ShotModel)
            .filter(ShotModel.sequence == sequence and ShotModel.name == name)
            .order_by(ShotModel.index.desc())
        )
        result = session.execute(query_previous_shot)
        previous_shot = result.scalar()
        if previous_shot:
            index = previous_shot.index + 1
        else:
            index = 0
        new_shot = ShotModel(
            sequence=sequence,
            name=name,
            index=index,
            start_time=start_time,
            end_time=end_time,
        )
        session.add(new_shot)
        session.flush()
        return new_shot

    def add_data(self, data: dict[str, Any], type_: "DataType", session: Session):
        for key, value in data.items():
            data_sql = DataModel(
                shot=self,
                type_=type_,
                name=key,
                value=value,
            )
            session.add(data_sql)

        session.flush()

    def get_data(self, type_: "DataType", session: Session):
        query = select(DataModel).filter(
            DataModel.shot == self, DataModel.type_ == type_
        )
        return {data.name: data.value for data in session.scalars(query).all()}


class DataType(enum.Enum):
    PARAMETER = "parameter"
    MEASURE = "measure"
    ANALYSIS = "analysis"


class DataModel(Base):
    __tablename__ = "data"
    __table_args__ = (
        UniqueConstraint("shot_id", "type_", "name", name="data_identifier"),
    )

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    shot_id: Mapped[int] = mapped_column(ForeignKey("shot.id"), index=True)
    shot: Mapped["ShotModel"] = relationship(back_populates="data")
    type_: Mapped[DataType] = mapped_column()
    name: Mapped[str] = mapped_column()
    value = Column(PickleType)
