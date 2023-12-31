class PostgreSQLExperimentSessionMaker(ExperimentSessionMaker):
    def __init__(
        self,
        user: str,
        ip: str,
        password: str,
        database: str,
    ):
        self._kwargs = {
            "user": user,
            "ip": ip,
            "password": password,
            "database": database,
        }
        database_url = f"postgresql+psycopg2://{user}:{password}@{ip}/{database}"
        self._engine = sqlalchemy.create_engine(database_url)
        self._session_maker = sqlalchemy.orm.sessionmaker(self._engine)

    def __call__(self) -> ExperimentSession:
        """Create a new ExperimentSession with the parameters given at initialization."""

        return SQLExperimentSession(self._session_maker())

    # The following methods are required to make ExperimentSessionMaker pickleable to
    # pass it to other processes. Since sqlalchemy engine is not pickleable, so we just
    # pickle the database info and create a new engine upon unpickling.
    def __getstate__(self) -> dict:
        return self._kwargs

    def __setstate__(self, state: dict):
        self.__init__(**state)
