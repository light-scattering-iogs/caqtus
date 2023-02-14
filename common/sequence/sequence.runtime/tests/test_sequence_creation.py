from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from sequence.runtime import Sequence, SequencePath, SequenceNotFoundError

from .setup_database import SetupDatabase, sequence_config


class TestSequenceCreation(SetupDatabase):
    def test_sequence_creation(self, sequence_config):
        with self.session as session:
            before = datetime.now()
            Sequence.create_sequence(
                SequencePath("year.month.day.name"), sequence_config, None, session
            )
            after = datetime.now()

            # creation date is correct
            creation_date = Sequence(
                SequencePath("year.month.day.name")
            ).get_creation_date(session)
            assert before <= creation_date <= after

            # Cannot access a sequence that does not exist
            with pytest.raises(SequenceNotFoundError):
                _ = Sequence(
                    SequencePath("year.month.day.other_name"),
                ).get_creation_date(session)

            # Cannot create a sequence twice
            with pytest.raises(RuntimeError):
                Sequence.create_sequence(
                    SequencePath("year.month.day.name"),
                    sequence_config,
                    None,
                    session,
                )

            # Cannot create a sequence with an ancestor
            with pytest.raises(RuntimeError):
                Sequence.create_sequence(
                    SequencePath("year.month.day.name.other"),
                    sequence_config,
                    None,
                    session,
                )

            # Cannot create a sequence with a descendant
            with pytest.raises(RuntimeError):
                Sequence.create_sequence(
                    SequencePath("year.month.day"),
                    sequence_config,
                    None,
                    session,
                )

            Sequence.create_sequence(
                SequencePath("year.month.day.other_name"),
                sequence_config,
                None,
                session,
            )



    def test_shot_creation(self, sequence_config):
        with self.session as session:
            now = datetime.now()
            sequence = Sequence.create_sequence(
                SequencePath("test_sequence"), sequence_config, None, session
            )
            sequence.create_shot("shot", now, now, session)
            shot = sequence.create_shot("shot", now, now, session)
            assert shot.index == 1
            assert len(sequence.get_shots(session)) == 2

            data = {"test": 42, "test1": "test"}
            shot.add_measures(data, session)
            assert shot.get_measures(session) == data

            parameters = {"var1": 0, "var2": 1}
            shot.add_parameters(parameters, session)
            assert shot.get_parameters(session) == parameters

            with pytest.raises(IntegrityError):
                shot.add_measures(data, session)
