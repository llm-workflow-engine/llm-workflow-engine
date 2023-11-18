===============================================
Plugins
===============================================


-----------------------------------------------
Using plugins
-----------------------------------------------

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File-based plugins
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Place the plugin file in either:

* The main ``plugins`` directory of this module
* A ``plugins`` directory in your profile

Use the ``/config files`` command to see a list of currently configured plugin paths.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Package-based plugins
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Install the plugin package -- see below for a list of package plugins.


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Enabling plugins
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Enable the plugin in your configuration:

.. code-block:: yaml

   plugins:
     enabled:
       # This is a list of plugins to enable, each list item
       # should be the name of a plugin file.
       # For file-based plugins, this is the filename without the
       # extension.
       # For package-based plugins, see the installation instructions
       # for the package.
       - test

Note that setting ``plugins.enabled`` will overwrite the default enabled plugins. Use the ``/plugins`` command for a list of currently enabled plugins.


-----------------------------------------------
Core plugins
-----------------------------------------------

These plugins are built into LWE core:

* **echo:** Simple echo plugin, echos back the text you give it
* **examples:** Easily install example configuration files (see :ref:`Installing examples`)

They can be disabled by removing them from ``plugins.enabled`` in your configuration file.


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
* **provider_azure_openai_chat:** Access to `Azure OpenAI <https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models>`_ chat models
   https://github.com/llm-workflow-engine/lwe-plugin-provider-azure-openai-chat
* **provider_chat_anyscale:** Access to `Anyscale <https://docs.anyscale.com>`_ chat models
   https://github.com/llm-workflow-engine/lwe-plugin-provider-chat-anyscale
* **provider_chat_cohere:** Access to `Cohere <https://docs.cohere.com/docs/models>`_ chat models
   https://github.com/llm-workflow-engine/lwe-plugin-provider-chat-cohere
* **provider_chat_ollama:** Access to `Ollama <https://ollama.ai/library>`_ chat models
   https://github.com/llm-workflow-engine/lwe-plugin-provider-chat-ollama
* **provider_chat_vertexai:** Access to `Google Vertex AI <https://cloud.google.com/vertex-ai/docs/generative-ai/learn/models>`_ chat models.
   https://github.com/llm-workflow-engine/lwe-plugin-provider-chat-vertexai
* **provider_cohere:** Access to `Cohere <https://docs.cohere.com/docs/models>`_ models
   https://github.com/llm-workflow-engine/lwe-plugin-provider-cohere
* **provider_huggingface_hub:** Access to `Hugging Face Hub <https://huggingface.co/models>`_ models
   https://github.com/llm-workflow-engine/lwe-plugin-provider-huggingface-hub
* **provider_openai:** Access to non-chat `OpenAI <https://platform.openai.com/docs/models)>`_ models (GPT-3, etc.)
   https://github.com/llm-workflow-engine/lwe-plugin-provider-openai
* **provider_vertexai:** Access to `Google Vertex AI <https://cloud.google.com/vertex-ai/docs/generative-ai/learn/models>`_ text/code models.
   https://github.com/llm-workflow-engine/lwe-plugin-provider-vertexai


"""""""""""""""""""""""""""""""""""""""""""""""
Usage
"""""""""""""""""""""""""""""""""""""""""""""""

Use the ``/providers`` command for a list of currently enabled providers.

See ``/help provider`` for how to switch providers/models on the fly.

Example:

.. code-block:: console

   /provider openai
   /model model_name text-davinci-003


-----------------------------------------------
Writing plugins
-----------------------------------------------

There is currently no developer documentation for writing plugins.

The ``plugins`` directory has some default plugins, examining those will give a good idea for how to design a new one.
In particular, the ``echo`` plugin is well commented. The package plugins listed above also contain many different
approaches you can learn from.

To write new provider plugins, investigate the existing provider plugins as examples.

Currently, plugins for the shell can only add new commands.


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Plugin structure
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In order for plugins to load, a few simple conventions must be followed:

#. All plugins must inherit from the base :ref:`Plugin <lwe.core.plugin module>` class,
   and provide implementations of the ``setup()`` and ``default_config()`` methods.
   Class name should be a camel-cased version of the plugin name:

   .. code-block:: python

      from lwe.core.plugin import Plugin

      class ExamplePlugin(Plugin):
          """
          An example plugin, does blah blah blah...
          """

          # Implement these...
          @abstractmethod
          def setup(self):
              pass

          @abstractmethod
          def default_config(self):
              pass



   The first line of the class docstring will be used as the plugin description.

#. **Naming conventions:** Consider a plugin named ``example_plugin``:
    * **File-based plugin:** The filename must be the plugin name with a ``.py`` extension, ``example_plugin.py``
    * **Package-based plugin:** The the entry point must be ``lwe_plugins``, and the plugin name must be prefixed with ``lwe-plugin-``:

      .. code-block:: python

         setup(
             name="lwe-plugin-example-plugin",
             # Other setup options...
             entry_points={
                  "lwe_plugins": [
                      "lwe_plugin_example_plugin = lwe_plugin_example_plugin.plugin:ExamplePlugin"
                  ]
             },
         )

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Available objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

An instantiated plugin has access to these objects.

* ``self.config``: The current instantiated Config object
* ``self.log``: The instantiated Logger object
* ``self.backend``: The instantiated backend
* ``self.shell``: The instantiated shell
