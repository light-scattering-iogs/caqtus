import sys

import sqlalchemy
from PySide6.QtWidgets import QApplication
from sqlalchemy import event
from sqlalchemy.engine import Engine

from condetrol import CondetrolMainWindow
from core.session.sql import SQLExperimentSessionMaker, create_tables


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


url = "sqlite:///database.db"
engine = sqlalchemy.create_engine(url)

create_tables(engine)

session_maker = SQLExperimentSessionMaker(engine)

app = QApplication(sys.argv)
app.setApplicationName("Condetrol")

window = CondetrolMainWindow(session_maker)
with window:
    window.show()
    sys.exit(app.exec())
