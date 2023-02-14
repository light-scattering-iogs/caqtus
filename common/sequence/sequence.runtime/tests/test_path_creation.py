from sequence.runtime import SequencePath

from .setup_database import SetupDatabase


class TestPathCreation(SetupDatabase):
    def test_path_creation(self):
        with self.session as session:
            path = SequencePath("2023.02.12.test")
            path.create(session)
            for ancestor in path.get_ancestors(strict=False):
                assert ancestor.exists(session)

            path = SequencePath("2023.02.12.test.deeper")
            path.create(session)
            assert path.exists(session)
            assert path.is_folder(session)
