.. _presets_doc:

===============================================
Presets
===============================================

Presets allow you to conveniently manage various provider/model configurations.

As you use the CLI, you can execute a combination of ``/provider`` and ``/model``
commands to set up a provider/model configuration to your liking.

For example:

.. code-block:: console

   /provider chat_openai gpt-3.5-turbo
   /model temperature 0
   /model model_kwargs.top_p 0.2

Once you have the configuration set up, you can 'capture' it by saving it as a
preset.

To save an existing configuration as a preset:

.. code-block:: console

   /preset-save mypresetname

Later, to load that configuration for use:

.. code-block:: console

   /preset-load mypresetname

See ``/help`` for the various other preset commands.
