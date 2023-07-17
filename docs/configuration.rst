.. _configuration_doc:

===============================================
Configuration
===============================================

*Configuration is optional, default values will be used if no configuration profile is
provided.*


-----------------------------------------------
Viewing the current configuration
-----------------------------------------------


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
From the command line
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Run the program with the ``config`` argument:

.. code-block:: bash

   lwe config

You can also view just a portion of the config by providing a filter argument.

To view just the file/directory config:

.. code-block:: bash

   lwe config files


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
From a running instance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

   /config

This will show all the current configuration settings, the most important ones for installation are:

* **Config dir:** Where configuration files are stored
* **Current profile:** (shown in the ``Profile configuration`` section)
* **Config file:** The configuration file current being used
* **Data dir:** The data storage directory

From a running instance, you can also view just a portion of the configuration by providing a
filter argument:

.. code-block:: console

   /config model

...will show just the ``model`` portion of the configuration

A very handy filter is ``/config database``, which will show just the currently configured
database connection string.


-----------------------------------------------
Sample configuration
-----------------------------------------------

The default configuation settings can be seen in
`config.sample.yaml <https://github.com/llm-workflow-engine/llm-workflow-engine/blob/main/config.sample.yaml>`_
-- the file is well-commented with descriptions of the settings.

**DON'T just copy this file as your configuration!**

Instead, use it as a reference to tweak the configuration to your liking.

*NOTE:* Not all settings are available on all backends. See the example config for more information.

Command line arguments overrride custom configuration settings, which override default
configuration settings.

-------------------------------------------------
Editing the configuration for the current profile
-------------------------------------------------

1. Start the program: ``lwe``
2. Open the profile's configuration file in an editor: ``/config edit``
3. Edit file to taste and save

Most configuration options will be reloaded dynamically after the configuration file is saved,
otherwise a restart of the program is required.

-----------------------------------------------
Configuring model properties
-----------------------------------------------

To change the properties of a particular LLM model, use the ``/model`` command:

.. code-block:: console

   /model model_name gpt-3.5-turbo
   /model temperature 1.0

The ``/model`` command works within the models of the currently loaded :ref:`provider <Provider plugins>`.

*NOTE: The attributes that a particular model accepts are beyond the scope of this
document. While some attributes can be displayed via command completion in the
shell, you are advised to consult the API documentation for the specific provider
for a full list of available attributes and their values.*
