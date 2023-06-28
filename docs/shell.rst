===============================================
Shell
===============================================

For day-to-day hacking, LWE provides a robust command line interface.

-----------------------------------------------
Command line arguments
-----------------------------------------------

Run the command with the ``--help`` argument:

.. code-block:: bash

   lwe --help

-----------------------------------------------
One-shot mode
-----------------------------------------------

To run the CLI in one-shot mode, simply follow the command with the prompt you want to send to the LLM:

.. code-block:: bash

   lwe Hello World!

-----------------------------------------------
Interactive mode
-----------------------------------------------

To run the CLI in interactive mode, execute it with no additional arguments:

.. code-block:: bash

   lwe

Once the interactive shell is running, you can see a list of all commands with:

.. code-block:: bash

   /help

...or get help for a specific command with:

.. code-block:: bash

   /help <command>
