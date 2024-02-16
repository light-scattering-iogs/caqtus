Starting Condetrol
==================

Condetrol is the main window of the application.
It allows to create, display, edit and launch sequences on the setup.

Here is a simple example of how to get a Condetrol window running.
It won't be able to do much, but it will show the main window and can be configured more later.


Start with the necessary imports:

.. code-block:: python

    import sys

    import sqlalchemy
    from PySide6.QtWidgets import QApplication
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    from condetrol import CondetrolMainWindow
    from core.session.sql import SQLExperimentSessionMaker, create_tables


For this example we will use SQLite to store the data and configuration of the experiment.
SQLite is a simple and easy way to use a SQL database, and works well for small applications and testing.
It will store all data in a single file, which is easy to backup and move around.

This code snipped is necessary to enable `foreign key support in SQLite <https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#foreign-key-support>`_.
If these lines are missing, the application will not work as expected.
They should be placed before anything else that uses the database.

.. code-block:: python

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

If you plan to have a lot of data or access the data from several computers, you
should consider using a SQL server like PostgreSQL or MySQL (see ...), and in which case you should remove the previous lines.

Here we create the database engine using sqlalchemy.
This is the object that will be used to connect to the database and execute SQL commands.
In this example, we will store the data in the relative file "database.db".
This information is contained in the url string, which tells sqlalchemy how to connect to the database.
In addition to the file, the string also contains the type of database, in this case "sqlite".
For more configuration see the `engine documentation <https://docs.sqlalchemy.org/en/20/core/engines.html>`_.

.. code-block:: python

    url = "sqlite:///database.db"
    engine = sqlalchemy.create_engine(url)

Once the engine is created, we need to create the database tables using the :func:`core.session.sql.create_tables` function.
This function will create the missing tables in the database.
It is only required to run this function once, but it is safe to run it multiple times.

.. code-block:: python

    create_tables(engine)

At this point a new file "database.db" should have been created in the current directory.
It contains the tables required for the application to run, but is otherwise empty.
You can open it with a database browser if you want to see the structure, but it should not be necessary to read or edit the file manually.

Now the database is ready, but we still need to tell the application how to connect to it.
This is done by creating a :class:`core.session.sql.SQLExperimentSessionMaker` object.
This is an object that stores the information connection for the experiment storage and is used by the application to save and retrieve data independently of the storage backend.

.. code-block:: python

    session_maker = SQLExperimentSessionMaker(engine)

After this, we can create the graphical application.
This is done by creating a :class:`PySide6.QtWidgets.QApplication` object.
It is always necessary to create an application object before creating any graphical elements.

.. code-block:: python

    app = QApplication(sys.argv)
    app.setApplicationName("Condetrol")

Finally, we can create the main window and show it.
Note the use of the `with` statement for the window.
This is necessary to tell the window that it should start reading the content of the database.
If you forget it, you won't be able to see changes made to the database.

.. code-block:: python

    window = CondetrolMainWindow(session_maker)
    with window:
        window.show()
        sys.exit(app.exec())

After running this code, you should be greeted with a window that allows you to create and edit sequences.

You won't be able to run sequences yet, as you need to configure the setup and the devices first.