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

.. code-block:: console

   /help

...or get help for a specific command with:

.. code-block:: console

   /help <command>

-----------------------------------------------
Shell pipeline
-----------------------------------------------

LWE accepts input from a file using the ``--input-file`` argument.

If no file is provided, LWE will read input from STDIN.

Since LLM responses go to STDOUT, it can be used in a shell pipeline:

.. code-block:: bash

   echo "Say hello!" | lwe --input-file > /tmp/out

**NOTE:** Currently only text input to and output from the LLM is supported in this mode.
See `this issue <https://github.com/llm-workflow-engine/llm-workflow-engine/issues/318>`_ for plans
to support structured data on STDIN/STDOUT.
