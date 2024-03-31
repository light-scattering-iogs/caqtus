Starting Condetrol
==================

Condetrol is the main window of the application.
It lets you create, display, edit and launch sequences on the setup.

Here is a simple example of how to get a Condetrol window running.
It won't be able to do much, but it will show the main window and can be customized further down the line.

.. code-block:: python

    from caqtus.gui.condetrol import Condetrol
    from caqtus.session.sql import SQLExperimentSessionMaker

    if __name__ == "__main__":
        session_maker = SQLExperimentSessionMaker.from_url("sqlite:///database.db")
        session_maker.create_tables()

        app = Condetrol(session_maker)
        app.run()

To launch the application, we need to import and run the :class:`caqtus.gui.condetrol.Condetrol` class.

This class requires a :class:`caqtus.session.ExperimentSessionMaker` object to be passed to it when it is created.
A session maker contains all the information necessary to connect to the permanent storage of the experiment.
The window will use the methods of this object to store and read sequences.

Here we create a particular session maker, with type :class:`caqtus.session.sql.SQLExperimentSessionMaker`.
This session maker uses a SQL database to store the data.
In this example, we use an SQLite database and after running the script, you should notice a file called `database.db` that appeared.
All the sequences that you create and the data generated while running them will be stored in this file.

While storing everything in a single file is convenient, it is not the best long-term solution.
In particular, if you start generating several gigabytes of data, this will become a limit.
In addition, it is difficult to access the data from multiple computers.
If you plan to start using the application extensively, you should consider :ref:`setting up a SQL server <howto set up a sql server>` instead.