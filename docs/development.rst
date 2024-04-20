===============================================
Development
===============================================

We welcome contributions to LWE!

If you have an idea for a new feature or have found a bug, please
`open an issue <https://github.com/llm-workflow-engine/llm-workflow-engine/blob/main/ISSUES.md>`_
on the GitHub repository.

-----------------------------------------------
Development Dependencies
-----------------------------------------------

To install LWE in development mode, run the following from the project root:

.. code-block:: bash

   pip install -e .[dev]

-----------------------------------------------
Test suite
-----------------------------------------------

The project uses `Pytest <https://docs.pytest.org>`_.

To run all tests:

.. code-block:: bash

   pytest

-----------------------------------------------
Documentation
-----------------------------------------------

The project uses `Sphinx <https://www.sphinx-doc.org>`_.

To build the documentation:

.. code-block:: bash

   cd doc
   pip-compile requirements.in
   make html
