
===============================================
Installation
===============================================

-----------------------------------------------
Requirements
-----------------------------------------------

To use this repository, you need:

* ``setuptools`` installed. You can install it using ``pip install setuptools``. Make sure that you have the last version of pip: ``pip install --upgrade pip``
* A database backend (SQLite by default, any configurable in SQLAlchemy allowed).

-----------------------------------------------
From packages
-----------------------------------------------

Install the latest version of this software directly from github with pip:

.. code-block:: bash

   pip install git+https://github.com/mmabrouk/chatgpt-wrapper

-----------------------------------------------
From source (recommended for development)
-----------------------------------------------

* Install the latest version of this software directly from git:
   .. code-block:: bash

      git clone https://github.com/mmabrouk/chatgpt-wrapper.git
* Install the development package:
   .. code-block:: bash

      cd chatgpt-wrapper
      pip install -e .
