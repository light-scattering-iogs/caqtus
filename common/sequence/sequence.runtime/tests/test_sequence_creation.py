from datetime import datetime

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from sequence.configuration import SequenceConfig, SequenceSteps
from sequence.configuration.shot import ShotConfiguration
from sequence.runtime import Sequence, SequencePath, SequenceNotFoundError
from sequence.runtime.base import Base

DB_NAME = "test_database"

DB_URL = f"postgresql+psycopg2://caqtus:Deardear@localhost/{DB_NAME}"


@pytest.fixture
def clean_database():
    engine = sa.create_engine(DB_URL, echo=False)
    Base.metadata.create_all(engine)

    session_maker = sessionmaker(engine)

    return session_maker


@pytest.fixture
def sequence_config():
    return SequenceConfig(
        program=SequenceSteps(), shot_configurations={"shot": ShotConfiguration()}
    )


class TestSequenceCreation:
    def setup_class(self):
        engine = sa.create_engine(DB_URL, echo=False)

        Base.metadata.drop_all(engine)

        session = sa.orm.scoped_session(sa.orm.sessionmaker())
        session.configure(bind=engine)
        Base.metadata.create_all(engine)

    def teardown_class(self):
        pass

    def test_sequence_creation(self, clean_database: sessionmaker, sequence_config):
        with clean_database() as session:
            before = datetime.now()
            Sequence.create_sequence(
                SequencePath("year.month.day.name"), sequence_config, None, session
            )
            after = datetime.now()

            # creation date is correct
            creation_date = Sequence(
                SequencePath("year.month.day.name")
            ).get_creation_date(session)
            assert before <= creation_date <= after

            # Cannot access a sequence that does not exist
            with pytest.raises(SequenceNotFoundError):
                _ = Sequence(
                    SequencePath("year.month.day.other_name"),
                ).get_creation_date(session)

            # Cannot create a sequence twice
            with pytest.raises(RuntimeError):
                Sequence.create_sequence(
                    SequencePath("year.month.day.name"),
                    sequence_config,
                    None,
                    session,
                )

            # Cannot create a sequence with an ancestor
            with pytest.raises(RuntimeError):
                Sequence.create_sequence(
                    SequencePath("year.month.day.name.other"),
                    sequence_config,
                    None,
                    session,
                )

            # Cannot create a sequence with a descendant
            with pytest.raises(RuntimeError):
                Sequence.create_sequence(
                    SequencePath("year.month.day"),
                    sequence_config,
                    None,
                    session,
                )


    def test_shot_creation(self, clean_database, sequence_config):
        with clean_database() as session:
            now = datetime.now()
            sequence = Sequence.create_sequence(
                SequencePath("test_sequence"), sequence_config, None, session
            )
            sequence.create_shot("shot", now, now, session)
            shot = sequence.create_shot("shot", now, now, session)
            assert shot.index == 1
            assert len(sequence.get_shots(session)) == 2

            data = {"test": 42, "test1": "test"}
            shot.add_measures(data, session)
            assert shot.get_measures(session) == data

            parameters = {"var1": 0, "var2": 1}
            shot.add_parameters(parameters, session)
            assert shot.get_parameters(session) == parameters

            with pytest.raises(IntegrityError):
                shot.add_measures(data, session)
