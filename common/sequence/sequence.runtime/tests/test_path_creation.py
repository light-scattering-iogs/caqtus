from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from sequence.runtime import SequencePath
from sequence.runtime.base import Base

DB_NAME = "test_database"

DB_URL = f"postgresql+psycopg2://caqtus:Deardear@localhost/{DB_NAME}"


class TestPathCreation:
    def setup_class(self):
        engine = create_engine(DB_URL, echo=False)

        Base.metadata.drop_all(engine)

        self.session = scoped_session(sessionmaker())
        self.session.configure(bind=engine)
        Base.metadata.create_all(engine)

    def teardown_class(self):
        pass

    def test_path_creation(self):
        with self.session() as session:
            path = SequencePath("2023.02.12.test")
            path.create(session)
            for ancestor in path.get_ancestors(strict=False):
                assert ancestor.exists(session)

            path = SequencePath("2023.02.12.test.deeper")
            path.create(session)
            assert path.exists(session)
            assert path.is_folder(session)

            path = SequencePath("2023.02.12")

            print(path.get_children(session))
