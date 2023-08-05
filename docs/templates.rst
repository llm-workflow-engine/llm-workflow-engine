===============================================
Templates
===============================================

LWE comes with a full template management system, leveraging the power of the venerable `Jinja <https://jinja.palletsprojects.com/en/3.1.x/>`_ framework.

Templates allow storing text in template files, and quickly leveraging the contents as your user input.

Features:

 * Create/edit templates
 * Per-profile templates
 * ``{{ variable }}`` syntax substitution
 * Five different workflows for collecting variable values, editing, and running

See the various ``/help template`` commands for more information.


-----------------------------------------------
Builtin variables
-----------------------------------------------

LWE exposes some builtin variables that can be used in templates:

 * ``{{ clipboard }}`` - Insert the contents of the clipboard


-----------------------------------------------
Front matter
-----------------------------------------------

Templates may include front matter (see the `example templates <https://github.com/llm-workflow-engine/llm-workflow-engine/tree/main/examples/templates>`_).

These front matter attributes have special functionality:

* ``description``: Displayed in the output of ``/templates``
* ``request_overrides``: A hash of model customizations to apply when the template is run:
   * ``system_message``: An existing system message alias, or a custom system message to use when running the template
   * ``title``: Sets the title of new conversations to this value
   * ``preset``: An existing preset for the provider/model configuration to use when running the template (see :ref:`presets_doc`)
   * ``activate_preset``: By default, a preset set in a template is only used during the run of the template. To switch the backend to using the preset for other requests by default, set this to ``true``
   * ``preset_overrides``: A dictionary of metadata and model customization overrides to apply to the preset when running the template
      * ``metadata``: A dictionary of metadata overrides
      * ``model_customizations```: A dictionary of model customization overrides

     This dictionary is recursively merged with the struture of the preset configuration. To see the exact structure of a preset,
     use the ``/preset-edit`` command.

All other attributes will be passed to the template as variable substitutions.
