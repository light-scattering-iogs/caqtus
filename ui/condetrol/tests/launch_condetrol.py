import logging.config
import sys

import sqlalchemy
from PySide6.QtWidgets import QApplication
from sqlalchemy import event
from sqlalchemy.engine import Engine

from condetrol import CondetrolMainWindow
from core.session import ParameterNamespace
from core.session.sql import SQLExperimentSessionMaker, create_tables
from core.types.expression import Expression
from core.types.variable_name import VariableName

log_config = {
    "version": 1,
    "formatters": {
        "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "default": {
            "level": "DEBUG",
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "": {"level": "WARNING", "handlers": ["default"]},
        "condetrol.parameters_editor": {"level": "DEBUG"},
        # "sequence_hierarchy": {"level": "DEBUG"},
    },
}

logging.config.dictConfig(log_config)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


url = "sqlite:///database.db"
engine = sqlalchemy.create_engine(url)

create_tables(engine)

session_maker = SQLExperimentSessionMaker(engine)

with session_maker() as session:
    sequence = session.sequences["\\new sequence"]
    sequence.set_parameters(
        ParameterNamespace.from_mapping(
            {
                VariableName("namespace"): {
                    VariableName("new_parameter"): Expression("1.0")
                }
            }
        ),
        session,
    )

app = QApplication(sys.argv)
app.setStyle("Fusion")
app.setApplicationName("Condetrol")

window = CondetrolMainWindow(session_maker)
with window:
    window.show()
    sys.exit(app.exec())
