import pytest
from pytest_postgresql import factories

from caqtus.session.sql import PostgreSQLConfig

postgresql_empty_no_proc = factories.postgresql_noproc()

postgresql_empty = factories.postgresql("postgresql_empty_no_proc")


def to_postgresql_config(p) -> PostgreSQLConfig:
    return PostgreSQLConfig(
        username=p.info.user,
        password=p.info.password,
        host=p.info.host,
        port=p.info.port,
        database=p.info.dbname,
    )


@pytest.fixture
def empty_database_config(postgresql_empty) -> PostgreSQLConfig:
    return to_postgresql_config(postgresql_empty)
