from __future__ import annotations

import sqlalchemy
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ._path_table import SQLSequencePath
from ._table_base import Base
from ..sequence.state import State


class SQLIterationConfiguration(Base):
    __tablename__ = "iteration_configurations"

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    iteration_type: Mapped[str] = mapped_column()
    content = mapped_column(sqlalchemy.types.JSON)


class SQLSequence(Base):
    __tablename__ = "sequence"

    id_: Mapped[int] = mapped_column(name="id", primary_key=True)
    path_id: Mapped[str] = mapped_column(
        ForeignKey(SQLSequencePath.id_), unique=True, index=True
    )
    path: Mapped[SQLSequencePath] = relationship(back_populates="sequence")

    iteration_config_id: Mapped[int] = mapped_column(
        ForeignKey(SQLIterationConfiguration.id_), unique=True
    )
    iteration_config: Mapped[SQLIterationConfiguration] = relationship(cascade="all")
    state: Mapped[State]
    device_uuids: Mapped[set[SQLSequenceDeviceUUID]] = relationship(
        cascade="all, delete, delete-orphan"
    )
    constant_table_uuids: Mapped[set[SQLSequenceConstantTableUUID]] = relationship(
        cascade="all, delete, delete-orphan"
    )

    #
    # config_id: Mapped[int] = mapped_column(
    #     ForeignKey("sequence_config.id"), unique=True
    # )
    # config: Mapped[SequenceConfig] = relationship(cascade="all")
    #
    # experiment_config_name: Mapped[Optional[str]] = mapped_column(
    #     ForeignKey("experiment_config.name")
    # )
    # experiment_config: Mapped[Optional[ExperimentConfig]] = relationship(viewonly=True)
    #
    # creation_date: Mapped[datetime] = mapped_column()
    # modification_date: Mapped[datetime] = mapped_column()
    # start_date: Mapped[Optional[datetime]] = mapped_column()
    # stop_date: Mapped[Optional[datetime]] = mapped_column()
    #
    # total_number_shots: Mapped[
    #     Optional[int]
    # ] = mapped_column()  # None indicates that this number is unknown
    # number_completed_shots: Mapped[int] = mapped_column()
    #
    # shots: Mapped[list[Shot]] = relationship(
    #     cascade="all, delete, delete-orphan", passive_deletes=True
    # )
    #
    # def __repr__(self):
    #     return (
    #         f"SequenceModel(path={self.path}, state={self.state},"
    #         f" creation_date={self.creation_date},"
    #         f" modification_date={self.modification_date},"
    #         f" start_date={self.start_date}, stop_date={self.stop_date})"
    #     )
    #
    # @classmethod
    # def create_sequence(
    #     cls,
    #     path: str,
    #     sequence_config: JSON,
    #     experiment_config_name: Optional[str],
    #     session: Session,
    # ):
    #     query_path_id = select(SequencePathModel.id_).filter(
    #         SequencePathModel.path == Ltree(path)
    #     )
    #     path_id = session.scalar(query_path_id)
    #
    #     now = datetime.now()
    #     config = SequenceConfigModel(sequence_config_yaml=sequence_config.to_yaml())
    #     sequence_sql = SequenceModel(
    #         path_id=path_id,
    #         state=State.DRAFT,
    #         config=config,
    #         creation_date=now,
    #         modification_date=now,
    #         start_date=None,
    #         stop_date=None,
    #         total_number_shots=sequence_config.compute_total_number_of_shots(),
    #         number_completed_shots=0,
    #         experiment_config_name=experiment_config_name,
    #     )
    #     session.add(sequence_sql)
    #     session.flush()
    #     return sequence_sql
    #
    # def get_state(self) -> State:
    #     return self.state
    #
    # # noinspection PyTypeChecker
    # def set_state(self, new_state: State):
    #     previous_state = self.get_state()
    #     if not State.is_transition_allowed(previous_state, new_state):
    #         raise ValueError(
    #             f"Sequence state can't transition from {previous_state} to {new_state}"
    #         )
    #     if new_state == State.PREPARING:
    #         if not self.experiment_config:
    #             raise RuntimeError(
    #                 "Cannot set state to PREPARING without having a set experiment"
    #                 " config"
    #             )
    #         else:
    #             self.state = State.PREPARING
    #     elif new_state == State.CRASHED:
    #         if self.start_date:
    #             self.stop_date = datetime.now()
    #         self.state = State.CRASHED
    #     elif new_state == State.RUNNING:
    #         self.start_date = datetime.now()
    #         self.state = State.RUNNING
    #     elif new_state == State.INTERRUPTED:
    #         self.stop_date = datetime.now()
    #         self.state = State.INTERRUPTED
    #     elif new_state == State.FINISHED:
    #         self.stop_date = datetime.now()
    #         self.state = State.FINISHED
    #     elif new_state == State.DRAFT:
    #         self.experiment_config_name = None
    #         self.start_date = None
    #         self.stop_date = None
    #         self.number_completed_shots = 0
    #         self.shots.clear()
    #         self.state = State.DRAFT
    #     else:
    #         raise NotImplementedError()
    #
    # def set_experiment_config(self, experiment_config_name: str):
    #     # noinspection PyTypeChecker
    #     self.experiment_config_name = experiment_config_name
    #
    # def get_experiment_config(self) -> Optional[ExperimentConfigModel]:
    #     return self.experiment_config
    #
    # def get_number_completed_shots(self) -> int:
    #     return self.number_completed_shots
    #
    # def increment_number_completed_shots(self):
    #     if self.total_number_shots is not None:
    #         if self.number_completed_shots + 1 > self.total_number_shots:
    #             raise RuntimeError(
    #                 "Number of completed shots would be greater than the total number "
    #                 "of shots"
    #             )
    #     self.number_completed_shots += 1


class SQLSequenceDeviceUUID(Base):
    __tablename__ = "sequence_device_configurations"

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "sequence_id", "device_configuration_uuid", name="device_configuration"
        ),
    )

    id_: Mapped[int] = mapped_column(primary_key=True)
    sequence_id: Mapped[int] = mapped_column(ForeignKey(SQLSequence.id_))
    device_configuration_uuid = mapped_column(ForeignKey("device_configurations.uuid"))


class SQLSequenceConstantTableUUID(Base):
    __tablename__ = "sequence_constant_tables"

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "sequence_id", "constant_table_uuid", name="constant_table"
        ),
    )

    id_: Mapped[int] = mapped_column(primary_key=True)
    sequence_id: Mapped[int] = mapped_column(ForeignKey(SQLSequence.id_))
    constant_table_uuid = mapped_column(ForeignKey("constant_tables.uuid"))
