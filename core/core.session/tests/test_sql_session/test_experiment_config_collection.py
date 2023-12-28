import sqlalchemy

from core.session.sql import SQLExperimentSessionMaker, create_tables


def test():
    url = "sqlite:///database.db"
    engine = sqlalchemy.create_engine(url)

    create_tables(engine)

    session_maker = SQLExperimentSessionMaker(engine)

    with session_maker() as session:
        pass
