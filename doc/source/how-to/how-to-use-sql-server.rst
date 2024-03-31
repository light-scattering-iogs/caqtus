How to set up an SQL database
=============================

.. _howto set up a SQL server:

All applications in the project have a `session_maker` argument that they use to interact with the data storage.
This section describes how to set up an SQL database in which to store the data and how to create a :class:`caqtus.session.sql.SQLExperimentSessionMaker` that can be passed as the `session_maker` argument.

You need to choose between PostgreSQL, MySQL or SQLite and follow the corresponding instructions below.

PostgreSQL
----------

On the computer that will host the database, it is necessary to set up a PostgreSQL server.
Other machines can access the database remotely without needing to install the server.

#. Install PostgreSQL server

   #. Download the `PostgresSQL installer <https://www.postgresql.org/download/>`_.

   #. Launch the installer.

   #. Choose the installation directory.

   #. Choose the components to install. The default selection is fine.

   #. Choose the data directory. This is the place where all the data will be stored, so be sure to select a location with enough space. This can be changed later on, but it is more difficult.

   #. Choose (and remember) a password for the superuser postgres. This is the user that has all the rights on the databases.

   #. Choose the port on which the server will listen. The default is 5432 and should be fine. You will need to ensure that this port is open in the firewall if you want to access the server from another machine.

   #. Choose the locale.

   #. Review the installation settings and finish the installation.

#. Create the database

   #. Open the pgAdmin program. This is a graphical interface to manage the PostgreSQL server.

   #. Connect to the PostgreSQL server in the left panel. This will ask for the password of the superuser postgres.

   #. (Optional) Create a new user. This is not necessary, but it is recommended to create a user with limited rights to access the database. To do this, right-click on the Login/Group Roles node and select Create > Login/Group Role. Fill in the name, password and rights of the user and click OK.

   #. Create a new database. Right-click on the Databases node and select Create > Database. Fill in the name of the database and the owner (the user created in the previous step) and click OK.

#. Create the tables

   #. Install the psycopg2 package. This can be done with the following command:

      .. code-block:: bash

        pip install psycopg2

   #. Use the following script to create a session maker that can connect to the database and create the tables.

      .. code-block:: python

        from caqtus.session.sql import SQLExperimentSessionMaker

        # Replace user, password, server_ip (can be localhost) and database with the appropriate values
        session_maker = SQLExperimentSessionMaker.from_url(
            "postgresql+psycopg2://user:password@server_ip/database"
        )

        session_maker.create_tables()

At this point, the database is ready to be used.
You can use the session maker to interact with the database.
It is not necessary to create the tables every time you want to use the database.

If you want to access the database from another machine, you will need to open the port 5432 in the firewall of the server and use the IP address of the server in the URL of the session maker from the client machine.

MySQL
-----

On the computer that will host the database, it is necessary to set up a MySQL server.
Other machines can access the database remotely without needing to install the server.

#. Install MySQL server

   #. Download the `MySQL installer <https://dev.mysql.com/downloads/installer/>`_.

   #. Launch the installer.

   #. Choose to install MySQL Server only.

   #. Run the installer.

   #. Configure the server. Default settings are recommended.

   #. Choose a password for the root user. This is the user that has all the rights on the databases.

   #. (Optional) Create new users and set up their rights.

   #. Configure the server to start automatically.

#. Create the database

   #. Open MySQL command line client.

   #. Connect to the server with the root user. This will ask for the password.

   #. Create a new database with the following command:

      .. code-block:: sql

        CREATE DATABASE database_name;

   #. (Optional) Create a new user with the following command:

      .. code-block:: sql

        CREATE USER 'user'@'localhost' IDENTIFIED BY 'password';

   #. (Optional) Grant the user access to the database with the following command:

      .. code-block:: sql

        GRANT ALL PRIVILEGES ON database_name.* TO 'user'@'localhost';

      If you want to access the database from another machine, you will need to replace 'localhost' with the IP address of the machine that will access the database.

#. Create the tables

   #. Install the pymysql package. This can be done with the following command:

      .. code-block:: bash

        pip install pymysql

   #. Use the following script to create a session maker that can connect to the database and create the tables.

      .. code-block:: python

        from caqtus.session.sql import SQLExperimentSessionMaker

        # Replace user, password, server_ip (can be localhost) and database with the appropriate values
        session_maker = SQLExperimentSessionMaker.from_url(
            "mysql+pymysql://user:password@server_ip/database"
        )

        session_maker.create_tables()

At this point, the database is ready to be used.
You can use the session maker to interact with the database.
It is not necessary to create the tables every time you want to use the database.




SQLite
------

SQLite is a light-weight database stored in a single file.
There is no server to install, just a file to create.
You can create a session maker with the following code:

.. code-block:: python

    from caqtus.session.sql import SQLExperimentSessionMaker

    # Replace the path with the path to the SQLite file
    session_maker = SQLExperimentSessionMaker.from_url(
        "sqlite:///path/to/sqlite.db"
    )

    session_maker.create_tables()

This will create a SQLite file in the specified path and create the tables in it.
Note however that SQLite is not recommended if your data starts to grow to large size or if you need to access the database from multiple machines.


