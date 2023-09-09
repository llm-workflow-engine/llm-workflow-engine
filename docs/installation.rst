===============================================
Installation
===============================================

-----------------------------------------------
Project code
-----------------------------------------------

Project code can be found at https://github.com/llm-workflow-engine/llm-workflow-engine

A list of available plugins can be found at https://llm-workflow-engine.readthedocs.io/en/latest/plugins.html#core-plugins

-----------------------------------------------
Requirements
-----------------------------------------------

To use this project, you need:

* Python 3.9 or later
* ``setuptools`` installed. You can install it using ``pip install setuptools``. Make sure that you have the last version of pip: ``pip install --upgrade pip``
* A database backend (`SQLite <https://www.sqlite.org/>`_ by default, any configurable in `SQLAlchemy <https://www.sqlalchemy.org/>`_ allowed).

-----------------------------------------------
From packages
-----------------------------------------------

Install the latest version of this software directly from github with pip:

.. code-block:: bash

   pip install git+https://github.com/llm-workflow-engine/llm-workflow-engine

-----------------------------------------------
From source (recommended for development)
-----------------------------------------------

* Install the latest version of this software directly from git:
   .. code-block:: bash

      git clone https://github.com/llm-workflow-engine/llm-workflow-engine.git

* Install the development package:
   .. code-block:: bash

      cd llm-workflow-engine
      pip install -e .

-----------------------------------------------
Notes for Windows users
-----------------------------------------------

Most other operating systems come with SQLite (the default database choice) installed, Windows may not.

If not, you can grab the 32-bit or 64-bit DLL file from https://www.sqlite.org/download.html, then place the DLL in ``C:\Windows\System32`` directory.

You also may need to install Python, if so grab the latest stable package from https://www.python.org/downloads/windows/ -- make sure to select the install option to ``Add Python to PATH``.

For the ``/editor`` command to work, you'll need a command line editor installed and in your path. You can control which editor is used by setting the ``EDITOR`` environment variable to the name of the editor executable, e.g. ``nano`` or ``vim``.

-----------------------------------------------
Installing examples
-----------------------------------------------

LWE provides several features that are controlled by adding correctly formatted configuration files to a specific configuration subdirectory:

* Templates
* Workflows
* Model presets
* OpenAI function definitions

If you'd like to jump start your setup with some examples of each, you can use the ``examples`` plugin (enabled by default).

To list the examples available, and where they will be installed:

.. code-block:: console

   /examples list

To install all the examples:

.. code-block:: console

   /examples

To install examples for a specific feature (e.g. templates):

.. code-block:: console

   /examples templates
