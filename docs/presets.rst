.. _presets_doc:

===============================================
Presets
===============================================

Presets allow you to conveniently manage various provider/model configurations.

As you use the CLI, you can execute a combination of ``/provider`` and ``/model``
commands to set up a provider/model configuration to your liking.

Once you have the configuration set up, you can 'capture' it by saving it as a
preset.

To save an existing configuration as a preset:

.. code-block:: bash

   /preset-save mypresetname

Later, to load that configuration for use:

.. code-block:: bash

   /preset-load mypresetname

See ``/help`` for the various other preset commands.
