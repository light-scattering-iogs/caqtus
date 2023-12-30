import pytest
import sqlalchemy
from core.configuration import Expression
from core.session import ExperimentSession
from core.session.sql import (
    SQLExperimentSessionMaker,
    create_tables,
)
from elliptec_ell14.configuration import (
    ElliptecELL14RotationStageConfiguration,
    dump,
    load,
)


def create_empty_session() -> ExperimentSession:
    url = "sqlite:///:memory:"
    engine = sqlalchemy.create_engine(url)

    create_tables(engine)

    session_maker = SQLExperimentSessionMaker(
        engine,
        {"ElliptecELL14RotationStageConfiguration": {"dumper": dump, "loader": load}},
    )
    return session_maker()


@pytest.fixture(scope="function")
def empty_session():
    return create_empty_session()


def test_1(empty_session):
    config = ElliptecELL14RotationStageConfiguration(
        serial_port="COM0",
        device_id=0,
        position=Expression("1"),
    )
    with empty_session as session:
        session.device_configurations["test"] = config

        config_1 = session.device_configurations["test"]
        assert config_1 == config

        session.device_configurations["test"] = config

        del session.device_configurations["test"]
        with pytest.raises(KeyError):
            session.device_configurations["test"]
