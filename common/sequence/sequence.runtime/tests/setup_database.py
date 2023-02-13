import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from sequence.configuration import SequenceConfig, ShotConfiguration, SequenceSteps
from sequence.runtime.base import Base

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

        self.session = scoped_session(sessionmaker())
        self.session.configure(bind=engine)
        Base.metadata.create_all(engine)

    def teardown_class(self):
        pass
