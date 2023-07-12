===============================================
Upgrading
===============================================


-----------------------------------------------
PLEASE HEED THESE IMPORTANT WARNINGS
-----------------------------------------------

1. This is a pre-release project
    * Breaking changes are happening regularly
    * **Before you upgrade and before you file any issues related to upgrading, refer to the `Breaking Changes` section for all releases since your last upgrade.**
2. Back up your database and configuration settings
    * Some releases include changes to the database schema and/or configuration files
    * **If you care about any data stored by this project, back it up before upgrading**
    * Common upgrade scenarios are tested with the default database (SQLite), but data integrity is **not** guaranteed
    * If any database errors occur during an upgrade, roll back to an earlier release and `open an issue <https://github.com/llm-workflow-engine/llm-workflow-engine/blob/main/ISSUES.md>`_


-----------------------------------------------
Via pip
-----------------------------------------------

Until an official release exists, you'll need to uninstall and reinstall:

.. code-block:: bash

   pip uninstall -y llm-workflow-engine
   pip install git+https://github.com/llm-workflow-engine/llm-workflow-engine


-----------------------------------------------
Via git
-----------------------------------------------

If the package was installed via ``pip install -e``, simply pull in the latest changes from the repository
and re-run the development installation:

.. code-block:: bash

   git pull
   pip install -e .
