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
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    Session,
    relationship,
    remote,
    foreign,
    backref,
)
from sqlalchemy_utils import Ltree, LtreeType

from sequence.configuration import SequenceConfig
from .base import Base
from .sequence_state import State

if typing.TYPE_CHECKING:
    pass


# Need to activate Ltree extension in Postgresql
# In the psql shell:
# CREATE EXTENSION IF NOT EXISTS ltree;


class ExperimentConfigModel(Base):
    __tablename__ = "experiment_config"

    name: Mapped[str] = mapped_column(primary_key=True, index=True)
    experiment_config_yaml: Mapped[str] = mapped_column()
    comment: Mapped[Optional[str]] = mapped_column()
    modification_date: Mapped[datetime] = mapped_column(index=True)

    @classmethod
    def add_config(cls, name: str, yaml: str, comment: Optional[str], session: Session):
        new_config = cls(
            name=name,
            experiment_config_yaml=yaml,
            comment=comment,
            modification_date=datetime.now(),
        )
        session.add(new_config)
        session.flush()

    @classmethod
    def get_configs(
        cls,
        from_date: Optional[datetime],
        to_date: Optional[datetime],
        session: Session,
    ) -> dict[datetime, str]:
        if from_date is None:
            from_date = datetime.min
        if to_date is None:
            to_date = datetime.max

        query = (
            select(cls)
            .where(cls.modification_date.between(from_date, to_date))
            .order_by(cls.modification_date)
        )
        return {
            result.name: result.experiment_config_yaml
            for result in session.scalars(query)
        }

    @classmethod
    def get_config(cls, name: str, session: Session) -> str:
        query = select(cls).where(cls.name == name)
        result = session.scalar(query)
        if result is None:
            raise ValueError(f"Config {name} does not exist")
        return result.experiment_config_yaml


class CurrentExperimentConfigModel(Base):
    """Represent a table with a single row to store the current experiment config"""

    __tablename__ = "current_experiment_config"

    current_experiment_config_name: Mapped[str] = mapped_column(
        ForeignKey("experiment_config.name"), primary_key=True
    )
    current_experiment_config: Mapped[ExperimentConfigModel] = relationship(
        viewonly=True
    )

    @classmethod
    def set_current_experiment_config(cls, name: str, session: Session):
        query_current = select(cls)
        result = session.scalar(query_current)
        if result is None:
            new_current = cls(current_experiment_config_name=name)
            session.add(new_current)
        else:
            result.current_experiment_config_name = name
        session.flush()

    @classmethod
    def get_current_experiment_config_name(cls, session: Session) -> Optional[str]:
        query_current = select(cls)
        result = session.scalar(query_current)
        if result is None:
            return None
        return result.current_experiment_config_name


class SequencePathModel(Base):
    __tablename__ = "sequence_path"

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    path = Column(LtreeType, unique=True, nullable=False)
    creation_date: Mapped[datetime] = mapped_column()
    parent: Mapped[Optional["SequencePathModel"]] = relationship(
        primaryjoin=remote(path) == foreign(func.subpath(path, 0, -1)),
        backref=backref("children", cascade="all"),
    )
    sequence: Mapped[list["SequenceModel"]] = relationship(
        cascade="all"
    )  # the list will always contain either 0 or 1 element

    __table_args__ = (Index("ix_nodes_path", path, postgresql_using="gist"),)

    @classmethod
    def create_path(
        cls,
        path: str,
        session: Session,
    ):
        session.add(cls(path=Ltree(path), creation_date=datetime.now()))
        session.flush()

    def is_sequence(self) -> bool:
        return len(self.sequence) == 1

    def get_sequence(self) -> "SequenceModel":
        # noinspection PyTypeChecker
        return self.sequence[0]

    def __str__(self):
        return str(self.path)


class SequenceConfigModel(Base):
    __tablename__ = "sequence_config"

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    sequence_config_yaml: Mapped[str] = mapped_column()


class SequenceModel(Base):
    __tablename__ = "sequence"

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    path_id: Mapped[str] = mapped_column(
        ForeignKey("sequence_path.id"), unique=True, index=True
    )
    path: Mapped[SequencePathModel] = relationship(back_populates="sequence")
    state: Mapped[State]

    config_id: Mapped[int] = mapped_column(
        ForeignKey("sequence_config.id"), unique=True
    )
    config: Mapped[SequenceConfigModel] = relationship(cascade="all")

    experiment_config_name: Mapped[Optional[str]] = mapped_column(
        ForeignKey("experiment_config.name")
    )
    experiment_config: Mapped[Optional[ExperimentConfigModel]] = relationship(
        viewonly=True
    )

    creation_date: Mapped[datetime] = mapped_column()
    modification_date: Mapped[datetime] = mapped_column()
    start_date: Mapped[Optional[datetime]] = mapped_column()
    stop_date: Mapped[Optional[datetime]] = mapped_column()

    total_number_shots: Mapped[
        Optional[int]
    ] = mapped_column()  # None indicates that this number is unknown
    number_completed_shots: Mapped[int] = mapped_column()

    shots: Mapped[list["ShotModel"]] = relationship(cascade="all, delete-orphan")

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
        path: str,
        sequence_config: SequenceConfig,
        experiment_config_name: Optional[str],
        session: Session,
    ):
        query_path_id = select(SequencePathModel.id_).filter(
            SequencePathModel.path == Ltree(path)
        )
        path_id = session.scalar(query_path_id)

        now = datetime.now()
        config = SequenceConfigModel(sequence_config_yaml=sequence_config.to_yaml())
        sequence_sql = SequenceModel(
            path_id=path_id,
            state=State.DRAFT,
            config=config,
            creation_date=now,
            modification_date=now,
            start_date=None,
            stop_date=None,
            total_number_shots=sequence_config.compute_total_number_of_shots(),
            number_completed_shots=0,
            experiment_config_name=experiment_config_name,
        )
        session.add(sequence_sql)
        session.flush()
        return sequence_sql

    def get_state(self) -> State:
        return self.state

    # noinspection PyTypeChecker
    def set_state(self, new_state: State):
        previous_state = self.get_state()
        if not State.is_transition_allowed(previous_state, new_state):
            raise ValueError(
                f"Sequence state can't transition from {previous_state} to {new_state}"
            )
        if new_state == State.PREPARING:
            if not self.experiment_config:
                raise RuntimeError(
                    "Cannot set state to PREPARING without having a set experiment"
                    " config"
                )
            else:
                self.state = State.PREPARING
        elif new_state == State.CRASHED:
            if self.start_date:
                self.stop_date = datetime.now()
            self.state = State.CRASHED
        elif new_state == State.RUNNING:
            self.start_date = datetime.now()
            self.state = State.RUNNING
        elif new_state == State.INTERRUPTED:
            self.stop_date = datetime.now()
            self.state = State.INTERRUPTED
        elif new_state == State.FINISHED:
            self.stop_date = datetime.now()
            self.state = State.FINISHED
        elif new_state == State.DRAFT:
            self.experiment_config_name = None
            self.start_date = None
            self.stop_date = None
            self.number_completed_shots = 0
            self.shots[:] = []
            self.state = State.DRAFT
        else:
            raise NotImplementedError()

    def set_experiment_config(self, experiment_config_name: str):
        # noinspection PyTypeChecker
        self.experiment_config_name = experiment_config_name

    def get_experiment_config(self) -> Optional[ExperimentConfigModel]:
        return self.experiment_config

    def get_number_completed_shots(self) -> int:
        return self.number_completed_shots

    def increment_number_completed_shots(self):
        if self.total_number_shots is not None:
            if self.number_completed_shots + 1 > self.total_number_shots:
                raise RuntimeError(
                    "Number of completed shots would be greater than the total number "
                    "of shots"
                )
        self.number_completed_shots += 1


class ShotModel(Base):
    __tablename__ = "shot"
    __table_args__ = (
        UniqueConstraint("sequence_id", "name", "index", name="shot_identifier"),
    )

    id_: Mapped[int] = mapped_column(name="id", primary_key=True, index=True)
    sequence_id: Mapped[str] = mapped_column(ForeignKey("sequence.id"), index=True)
    sequence: Mapped["SequenceModel"] = relationship(back_populates="shots")
    name: Mapped[str] = mapped_column()
    index: Mapped[int] = mapped_column()

    start_time: Mapped[datetime] = mapped_column()
    end_time: Mapped[datetime] = mapped_column()

    data: Mapped[list["DataModel"]] = relationship(cascade="all, delete-orphan")

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
    SCORE = "score"


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
