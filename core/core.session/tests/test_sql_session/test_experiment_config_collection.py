import sqlalchemy

from core.session.sql import SQLExperimentSessionMaker, create_tables
from core.session import ExperimentConfig


def test_set_current():
    url = "sqlite:///:memory:"
    engine = sqlalchemy.create_engine(url)

    create_tables(engine)

    session_maker = SQLExperimentSessionMaker(engine)

    experiment_config = ExperimentConfig()

    with session_maker() as session:
        session.experiment_configs.set_current_config(experiment_config)
        assert session.experiment_configs.get_current_config() == experiment_config
