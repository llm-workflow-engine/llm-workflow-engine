===============================================
Installation
===============================================

-----------------------------------------------
Requirements
-----------------------------------------------

To use this repository, you need:

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
Installing examples
-----------------------------------------------

LWE provides several features that are controlled by adding correctly formatted configuration files to a specific configuration subdirectory:

* Templates
* Workflows
* Model presets
* OpenAI function definitions

If you'd like to jump start your setup with some examples of each, you can use the ``examples`` plugin (enabled by default).

To list the examples available, and where they will be installed:

.. code-block:: bash

   /examples list

To install all the examples:

.. code-block:: bash

   /examples

To install examples for a specific feature (e.g. templates):

.. code-block:: bash

   /examples templates
