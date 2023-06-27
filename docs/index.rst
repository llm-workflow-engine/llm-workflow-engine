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


.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: Contents:

   how_it_works
   installation
   initial_setup
   presets
   python_module
   modules


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
