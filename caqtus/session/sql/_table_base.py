import sqlalchemy.orm


class Base(sqlalchemy.orm.DeclarativeBase):
    pass


def create_tables(engine: sqlalchemy.engine.Engine) -> None:
    """Creates all tables in the database.

    This function only creates non-existing tables. It does not modify existing tables.
    """
