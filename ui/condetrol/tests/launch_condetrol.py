import sys

import sqlalchemy
from PySide6.QtWidgets import QApplication

from condetrol import CondetrolMainWindow
from core.session.sql import SQLExperimentSessionMaker, create_tables

url = "sqlite:///database.db"
engine = sqlalchemy.create_engine(url)

create_tables(engine)

session_maker = SQLExperimentSessionMaker(engine)


def main():
    app = QApplication(sys.argv)
    main_window = CondetrolMainWindow(session_maker)

    with main_window:
        main_window.show()
        app.exec()


main()
