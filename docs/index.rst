===============================================
LLM Workflow Engine
===============================================

LLM Workflow Engine (LWE) is a command-line tool and Python module that streamlines
common LLM-related tasks, such as:

* Managing reusable prompts
* Stress-testing prompts across different LLM configurations
* Designing multi-step workflows that involve LLMs.

At its heart, LWE has four main components:

#. **Conversation management:**
    * Start new conversations
    * Review/extend/remove old conversations
#. **Model configuration:**
    * Configure LLMs across different providers
    * Customize model attributes (temperature, etc.)
    * Save/reload existing configurations
#. **Prompt templates:**
    * Design/save new prompts
    * Include/pass variables to prompts during execution
    * Connect a specific prompt to a specific model configuration
#. **Workflows:**
    * Design multi-step workflows using YAML
    * Integrate prompt templates
    * Integrate model configurations
    * Save LLM interactions to conversations

When combined, these four components provide a lot of flexibility and power for working with LLMs.


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Other LWE nicities
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. **Plugins:**
    * Command plugins: Write a command for LWE that accomplishes some new task
    * Provider plugins: Easily add new LLM providers into the LWE ecosystem
#. **Custom system messages:** Easily create and use different system messages for supported providers
#. **Command completion:** Tab completion for most commands and arguments
#. **Managed database updates:** Automatic database upgrades for new releases
#. **Examples**: To help jump start your productivity
    * Prompt templates
    * Workflows
#. **Ansible-compatible playbooks**: Re-use LWE workflows inside a larger `Ansible <https://docs.ansible.com>`_ ecosystem
#. **Automatic conversation titles**: The LLM generates short titles for your conversations
#. **Token tracking**: For supported providers, see the number of tokens the current conversation would send in a request, and auto-prune messages from long conversations
#. **Customizable user prompt**
#. **Multi-user management**
#. **Streaming responses:** For supported providers
#. **Command line help**
#. **System clipboard integration**
#. **Edit prompts in your system editor (Vim, etc.)**

.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: Contents:


   how_it_works
   installation
   initial_setup
   configuration
   upgrading
   shell
   python_module
   plugins
   templates
   presets
   workflows
   functions
   model_access
   docker
   troubleshooting
   development
   modules


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
