===============================================
Plugins
===============================================


-----------------------------------------------
Using plugins
-----------------------------------------------

#. Place the plugin file in either:
    * The main ``plugins`` directory of this module
    * A ``plugins`` directory in your profile

   Use the ``/config`` command and look in the ``File configuration`` section for a list of currently configured plugin paths.

#. Enable the plugin in your configuration:

     .. code-block:: yaml

       plugins:
         enabled:
           # This is a list of plugins to enable, each list item
           # should be the name of a plugin file, without the
           # extension.
           - test

   Note that setting ``plugins.enabled`` will overwrite the default enabled plugins. Use the ``/config plugins`` command for a list of currently enabled plugins.


-----------------------------------------------
Core plugins
-----------------------------------------------

These plugins are built into LWE core:

* **echo:** Simple echo plugin, echos back the text you give it
* **examples:** Easily install example configuration files (see :ref:`Installing examples`)


-----------------------------------------------
LWE maintained plugins
-----------------------------------------------

These plugins are maintained by the LWE team, and are not part of LWE core -- they must be installed.

Instructions for installing and configuring each plugin can be found at the referenced repository for each plugin.


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Shell command plugins
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These plugins add additional commands to the shell:

* **awesome:** Use prompts from `Awesome ChatGPT Prompts <https://github.com/f/awesome-chatgpt-prompts>`_
   https://github.com/llm-workflow-engine/lwe-plugin-awesome
* **database:** Send natural language commands to a database **WARNING: POTENTIALLY DANGEROUS -- DATA INTEGRITY CANNOT BE GUARANTEED.**
   https://github.com/llm-workflow-engine/lwe-plugin-database
* **data_query:** Send natural language commands to a loaded file of structured data
   https://github.com/llm-workflow-engine/lwe-plugin-data-query
* **pastebin:** Post a conversation to https://pastebin.com
   https://github.com/llm-workflow-engine/lwe-plugin-pastebin
* **shell:** Transform natural language into a shell command, and optionally execute it **WARNING: POTENTIALLY DANGEROUS -- YOU ARE RESPONSIBLE FOR VALIDATING THE COMMAND RETURNED BY THE LLM, AND THE OUTCOME OF ITS EXECUTION.**
   https://github.com/llm-workflow-engine/lwe-plugin-shell
* **test:** Test plugin, echos back the command you give it
   https://github.com/llm-workflow-engine/lwe-plugin-test
* **zap:** Send natural language commands to Zapier actions: https://nla.zapier.com/get-started/
   https://github.com/llm-workflow-engine/lwe-plugin-zap


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Provider plugins
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These plugins add additional LLM providers:

*NOTE: Most provider plugins are NOT chat-based, and instead return a single response to any text input.
These inputs and responses are still managed as 'conversations' for storage purposes, using the same storage
mechanism the chat-based providers use.*


"""""""""""""""""""""""""""""""""""""""""""""""
Supported providers
"""""""""""""""""""""""""""""""""""""""""""""""

**NOTE:** While these provider integrations are working, none have been well-tested yet.

* **provider_ai21:** Access to `AI21 <https://docs.ai21.com/docs/jurassic-2-models>`_ models
   https://github.com/llm-workflow-engine/lwe-plugin-provider-ai21
* **provider_cohere:** Access to `Cohere <https://docs.cohere.com/docs/models>`_ models
   https://github.com/llm-workflow-engine/lwe-plugin-provider-cohere
* **provider_huggingface_hub:** Access to `Hugging Face Hub <https://huggingface.co/models>`_ models
   https://github.com/llm-workflow-engine/lwe-plugin-provider-huggingface-hub
* **provider_openai:** Access to non-chat `OpenAI <https://platform.openai.com/docs/models)>`_ models (GPT-3, etc.)
   https://github.com/llm-workflow-engine/lwe-plugin-provider-openai


"""""""""""""""""""""""""""""""""""""""""""""""
Usage
"""""""""""""""""""""""""""""""""""""""""""""""

Use the ``/providers`` command for a list of currently enabled providers.

See ``/help provider`` command for how to switch providers/models on the fly.

Example:

.. code-block:: bash

   /provider openai
   /model model_name text-davinci-003


-----------------------------------------------
Writing plugins
-----------------------------------------------

There is currently no developer documentation for writing plugins.

The ``plugins`` directory has some default plugins, examining those will give a good idea for how to design a new one.

Currently, plugins for the shell can only add new commands. An instantiated plugin has access to these resources:

* ``self.config``: The current instantiated Config object
* ``self.log``: The instantiated Logger object
* ``self.backend``: The instantiated backend
* ``self.shell``: The instantiated shell

To write new provider plugins, investigate the existing provider plugins as examples.
