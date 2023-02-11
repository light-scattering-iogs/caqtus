from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sequence.configuration import SequenceConfig, SequenceSteps
from sequence.configuration.shot import ShotConfiguration
from sequence.runtime import Sequence, SequenceNotFoundError
from sequence.runtime.base import Base


@pytest.fixture(scope="function")
def clean_database():
    engine = create_engine("sqlite://", echo=False)
    Base.metadata.create_all(engine)

    session_maker = sessionmaker(bind=engine)

    return session_maker


def test_sequence_creation(clean_database):
    before = datetime.now()
    Sequence.create_sequence(
        "year/month/day/name",
        SequenceConfig(
            program=SequenceSteps(), shot_configurations={"shot": ShotConfiguration()}
        ),
        None,
        clean_database,
    )
    after = datetime.now()
    creation_date = Sequence("year/month/day/name", clean_database).get_creation_date()

    assert before <= creation_date <= after

    with pytest.raises(SequenceNotFoundError):
        _ = Sequence("year/month/day/other_name", clean_database).get_creation_date()
