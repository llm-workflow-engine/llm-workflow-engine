===============================================
Initial setup
===============================================


-----------------------------------------------
API keys
-----------------------------------------------

Grab an OpenAI API key from https://platform.openai.com/account/api-keys

Export the key into your local environment:

.. code-block:: bash

   export OPENAI_API_KEY=<API_KEY>

Windows users, see `here <https://www.computerhope.com/issues/ch000549.htm>`_ for how to edit environment variables.

To tweak the configuration for the current profile, see :ref:`configuration_doc`


-----------------------------------------------
Default configuration
-----------------------------------------------

LWE comes with sensible configuration defaults, and most users can start using it immediately.

Still, it's a good idea to know how to view the configuration.

From the command line, simply run:

.. code-block:: bash

   lwe config


-----------------------------------------------
Database
-----------------------------------------------

The API backend requires a database server to store conversation data. LWE leverages `SQLAlchemy <https://www.sqlalchemy.org/>`_ for this.

The simplest supported database is `SQLite <https://www.sqlite.org/>`_ (which is already installed on most modern operating systems), but you can use any database that is supported by SQLAlchemy.

Check the `database` setting from the :ref:`Default configuration`, which will show you the currently configured connection string for a default SQLite database.

If you're happy with that setting, nothing else needs to be done -- the database will be created automatically in that location when you run the program.


-----------------------------------------------
Initial user creation and login
-----------------------------------------------

Once the database is configured, run the program with no arguments:

.. code-block:: bash

   lwe

It will recognize no users have been created, and prompt you to create the first user:

* **Username:** Required, no spaces or special characters
* **Email:** Optional
* **Password:** Optional, if not provided the user can log in without a password

You should be automatically logged in and ready to go!

Once you're logged in, you have full access to all commands.

**NOTE:** Once multiple users are created, you'll need to execute the ``/login`` command with the username to log in:

.. code-block:: console

   /login [username]

**IMPORTANT NOTE:** The user authorization system from the command line is *admin party* -- meaning every logged in user has admin privileges, including editing and deleting other users.


-----------------------------------------------
Setting a per-user default preset
-----------------------------------------------

LWE supports configuring a default preset per user.

To do so, run ``/user-edit`` -- selecting a default preset will be one of the options.

See :ref:`presets_doc` for more information on configuring presets.
