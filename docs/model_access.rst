===============================================
Model access
===============================================

Not all models are freely accessible, so keep this in mind when setting up any LLM provider.


-----------------------------------------------
GPT4
-----------------------------------------------

To use GPT-4, you must have been granted access to the model in your OpenAI account.

NOTE: If you have not been granted access, you'll probably see an error like this:

.. code-block:: console

   InvalidRequestError(message='The model: `gpt-4` does not exist', param=None, code='model_not_found', http_status=404, request_id=None)

There is nothing this project can do to fix the error for you -- contact OpenAI and request GPT-4 access.

Follow one of the methods below to utilize GPT-4 in this backend:


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Method 1: Set a default preset configured with GPT-4
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

See :ref:`presets_doc` to configure a preset using GPT-4

Add the preset to the config file as the default preset on startup:

.. code-block:: yaml

   # This assumes you created a preset named 'gpt-4'
   model:
     default_preset: gpt-4


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Method 2: Dynamically switch
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

From within the shell, execute this command:

.. code-block:: console

   /model model_name gpt-4

...or... if you're not currently using the 'chat_openai' provider:

.. code-block:: console

   /provider chat_openai gpt-4

