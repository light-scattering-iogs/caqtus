import pytest
import sqlalchemy

from core.session import ExperimentSession
from core.session.sequence.iteration_configuration import VariableDeclaration
from core.session.sql import (
    SQLExperimentSessionMaker,
    create_tables,
)
from core.types.expression import Expression
from core.types.variable_name import DottedVariableName


def create_empty_session() -> ExperimentSession:
    url = "sqlite:///:memory:"
    engine = sqlalchemy.create_engine(url)

    create_tables(engine)

    session_maker = SQLExperimentSessionMaker(
        engine,
        {},
    )
    return session_maker()


@pytest.fixture(scope="function")
def empty_session():
    return create_empty_session()


def test_1(empty_session):
    table = [
        VariableDeclaration(
            variable=DottedVariableName("a"),
            value=Expression("1"),
        ),
        VariableDeclaration(
            variable=DottedVariableName("b"),
            value=Expression("2"),
        ),
    ]

    with empty_session as session:
        session.constants["test"] = table

        table_1 = session.constants["test"]
        assert table_1 == table

        del session.constants["test"]
        with pytest.raises(KeyError):
            session.constants["test"]
