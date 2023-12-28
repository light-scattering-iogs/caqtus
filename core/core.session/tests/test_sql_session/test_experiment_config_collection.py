import pytest
import sqlalchemy

from core.session import ExperimentConfig, ExperimentSession
from core.session.sql import (
    SQLExperimentSessionMaker,
    create_tables,
)


@pytest.fixture(scope="function")
def empty_session() -> ExperimentSession:
    url = "sqlite:///:memory:"
    engine = sqlalchemy.create_engine(url)

    create_tables(engine)

    session_maker = SQLExperimentSessionMaker(engine)

    return session_maker()


def test_set_current(empty_session: ExperimentSession):
    experiment_config = ExperimentConfig()

    with empty_session as session:
        name = session.experiment_configs.set_current_config(experiment_config)
        assert session.experiment_configs.get_current_config() == experiment_config

    with empty_session as session:
        assert session.experiment_configs[name] == experiment_config
        session.experiment_configs["123"] = ExperimentConfig()
        assert set(session.experiment_configs) == {name, "123"}
