===============================================
Plugins
===============================================


-----------------------------------------------
Using plugins
-----------------------------------------------

#. Place the plugin file in either:
    * The main ``plugins`` directory of this module
    * A ``plugins`` directory in your profile

#. Enable the plugin in your configuration:

     .. code-block:: yaml

       plugins:
         enabled:
           # This is a list of plugins to enable, each list item
           # should be the name of a plugin file, without the
           # extension.
           - test

   Note that setting ``plugins.enabled`` will overwrite the default enabled plugins. Use the ``/config`` command for a list of default enabled plugins.


-----------------------------------------------
Core plugins
-----------------------------------------------

* **test:** Test plugin, echos back the command you give it
* **awesome:** Use a prompt from Awesome ChatGPT Prompts: https://github.com/f/awesome-chatgpt-prompts
* **database:** Send natural language commands to a database **WARNING: POTENTIALLY DANGEROUS -- DATA INTEGRITY CANNOT BE GUARANTEED.**
* **data_query:** Send natural language commands to a loaded file of structured data
* **shell:** Transform natural language into a shell command, and optionally execute it **WARNING: POTENTIALLY DANGEROUS -- YOU ARE RESPONSIBLE FOR VALIDATING THE COMMAND RETURNED BY THE LLM, AND THE OUTCOME OF ITS EXECUTION.**
* **zap:** Send natural language commands to Zapier actions: https://nla.zapier.com/get-started/


-----------------------------------------------
Provider plugins
-----------------------------------------------

**NOTE:** Most provider plugins are *not* chat-based, and instead return a single response to any text input.
These inputs and responses are still managed as 'conversations' for storage purposes, using the same storage
mechanism the chat-based providers use.


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Supported providers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**NOTE:** While these provider integrations are working, none have been well-tested yet.

* **provider_ai21:** Access to `AI21 <https://docs.ai21.com/docs/jurassic-2-models>`_ models
* **provider_cohere:** Access to `Cohere <https://docs.cohere.com/docs/models>`_ models
* **provider_huggingface_hub:** Access to `Huggingface Hub <https://huggingface.co/models>`_ models
* **provider_openai:** Access to non-chat `OpenAI <https://platform.openai.com/docs/models)>`_ models (GPT-3, etc.)


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Usage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To enable a supported provider, add it to ``plugins.enabled`` list in your configuration.

.. code-block:: yaml

   plugins:
     enabled:
       - provider_openai

Use the ``/providers`` command for a list of currently enabled providers.

Use the ``/help provider`` command for how to switch providers/models on the fly.


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
