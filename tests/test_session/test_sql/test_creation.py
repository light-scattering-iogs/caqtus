import pytest

from caqtus.extension import Experiment, upgrade_database
from caqtus.session.sql import PostgreSQLExperimentSessionMaker
from caqtus.session.sql._session_maker import InvalidDatabaseSchema


def test_example_postgres(empty_database_config):

    exp = Experiment()
    exp.configure_storage(empty_database_config)
    with pytest.raises(InvalidDatabaseSchema):
        exp.get_session_maker()

    upgrade_database(exp)

    session_maker = exp.get_session_maker()
    assert isinstance(session_maker, PostgreSQLExperimentSessionMaker)
    session_maker.check()
