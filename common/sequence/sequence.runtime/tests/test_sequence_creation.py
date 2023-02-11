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


@pytest.fixture
def sequence_config():
    return SequenceConfig(
        program=SequenceSteps(), shot_configurations={"shot": ShotConfiguration()}
    )


def test_sequence_creation(clean_database, sequence_config):
    before = datetime.now()
    Sequence.create_sequence(
        "year/month/day/name",
        sequence_config,
        None,
        clean_database,
    )
    after = datetime.now()

    # creation date is between correct
    creation_date = Sequence("year/month/day/name", clean_database).get_creation_date()
    assert before <= creation_date <= after

    # Cannot access a sequence that does not exist
    with pytest.raises(SequenceNotFoundError):
        _ = Sequence("year/month/day/other_name", clean_database).get_creation_date()

    # Cannot create a sequence twice
    with pytest.raises(RuntimeError):
        Sequence.create_sequence(
            "year/month/day/name",
            sequence_config,
            None,
            clean_database,
        )

    # Cannot create a sequence with an ancestor
    with pytest.raises(RuntimeError):
        Sequence.create_sequence(
            "year/month/day/name/other",
            sequence_config,
            None,
            clean_database,
        )

    # Cannot create a sequence with a descendant
    with pytest.raises(RuntimeError):
        Sequence.create_sequence(
            "year/month/day",
            sequence_config,
            None,
            clean_database,
        )
