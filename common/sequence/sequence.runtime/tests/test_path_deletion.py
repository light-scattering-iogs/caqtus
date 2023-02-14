import pytest
from sqlalchemy import select

from sequence.runtime import SequencePath, Sequence
from sequence.runtime.model import SequenceModel

# noinspection PyUnresolvedReferences
from .setup_database import SetupDatabase, sequence_config


class TestPathDeletion(SetupDatabase):
    def test_path_deletion(self, sequence_config):
        with self.session as session:
            path = SequencePath("2023.02.12.test")
            path.create(session)
            path.delete(session)
            assert not path.exists(session)

            path = SequencePath("2023.02.12.test.deeper")
            path.create(session)
            path_id = path._query_model(session.get_sql_session()).id_
            SequencePath("2023").delete(session)
            for ancestor in path.get_ancestors(strict=False):
                assert not ancestor.exists(session)

            sequence = Sequence.create_sequence(
                SequencePath("test_sequence"), sequence_config, None, session
            )
            sequence.path.delete(session, delete_sequences=True)

            query_sequence = select(SequenceModel).filter(
                SequenceModel.path_id == path_id
            )
            assert not list(session.get_sql_session().scalars(query_sequence))

            Sequence.create_sequence(
                SequencePath("test.sequence"), sequence_config, None, session
            )
            with pytest.raises(RuntimeError):
                SequencePath("test").delete(session, delete_sequences=False)
