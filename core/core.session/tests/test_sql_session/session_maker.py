import sqlalchemy

from core.session import ExperimentSessionMaker
from core.session.sql import (
    SQLExperimentSessionMaker,
    create_tables,
    default_serializer,
)


def get_session_maker() -> ExperimentSessionMaker:
    url = "sqlite:///:memory:"
    engine = sqlalchemy.create_engine(url)

    create_tables(engine)

    session_maker = SQLExperimentSessionMaker(engine, {}, default_serializer)

    return session_maker
