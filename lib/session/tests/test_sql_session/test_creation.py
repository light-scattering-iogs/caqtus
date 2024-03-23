import sqlalchemy

from caqtus.session.sql import create_tables


def test_creation():
    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    create_tables(engine)
