import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from experiment.session import ExperimentSession
from sequence.configuration import SequenceConfig, ShotConfiguration, SequenceSteps
from sql_model import Base

DB_NAME = "test_database"

DB_URL = f"postgresql+psycopg2://caqtus:Deardear@localhost/{DB_NAME}"


@pytest.fixture
def clean_database():
    engine = create_engine(DB_URL, echo=False)
    Base.metadata.create_all(engine)

    session_maker = sessionmaker(engine)

    return session_maker


@pytest.fixture
def sequence_config():
    return SequenceConfig(
        program=SequenceSteps(), shot_configurations={"shot": ShotConfiguration()}
    )


class SetupDatabase:
    def setup_class(self):
        engine = create_engine(DB_URL, echo=False)

        Base.metadata.drop_all(engine)

        Base.metadata.create_all(engine)

        self.session = ExperimentSession(DB_URL, commit=False)

    def teardown_class(self):
        pass
