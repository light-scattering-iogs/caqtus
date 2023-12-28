from ._tables import Base

import sqlalchemy


def create_tables(engine: sqlalchemy.Engine) -> None:
    """Creates all tables in the database.

    This function only creates non-existing tables. It does not modify existing tables.
    """

    Base.metadata.create_all(engine)
