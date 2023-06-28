===============================================
Templates
===============================================

LWE comes with a full template management system.

Templates allow storing text in template files, and quickly leveraging the contents as your user input.

Features:

 * Per-profile templates
 * Create/edit templates
 * ``{{ variable }}`` syntax substitution
 * Five different workflows for collecting variable values, editing, and running

See the various ``/help template`` commands for more information.


-----------------------------------------------
Builtin variables
-----------------------------------------------

The wrapper exposes some builtin variables that can be used in templates:

 * ``{{ clipboard }}`` - Insert the contents of the clipboard


-----------------------------------------------
Front matter
-----------------------------------------------

Templates may include front matter (see the `example templates <https://github.com/llm-workflow-engine/llm-workflow-engine/tree/main/examples/templates>`_).

These front matter attributes have special functionality:

* ``title``: Sets the title of new conversations to this value
* ``description``: Displayed in the output of ``/templates``
* ``request_overrides``: A hash of model customizations to apply when the template is run:
   * ``preset``: An existing preset for the provider/model configuration to use when running the template (see :ref:`presets_doc`)
   * ``system_message``: An existing system message alias, or a custom system message to use when running the template

All other attributes will be passed to the template as variable substitutions.
