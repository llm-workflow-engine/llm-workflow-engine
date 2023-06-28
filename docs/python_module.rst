.. _python_module_doc:

===============================================
Python module
===============================================

You can  use the ``ApiBackend`` class to interact directly with the LLMs.

Create an instance of the class and use the ``ask`` method to send a message to the LLM and receive the response. For example:

.. code-block:: python

   from lwe import ApiBackend

   bot = ApiBackend()
   success, response, message = bot.ask("Hello, world!")
   if success:
       print(response)
   else:
       raise RuntimeError(message)

The ``ask`` method takes a string argument representing the message to send to the LLM, and returns a tuple with the following values:

#. ``success``: Boolean indicating whether the operation succeeded.
#. ``response``: An object representing the response received *(usually just a string response from the LLM)*
#. ``message``: User message describing the outcome of the operation.

To pass custom configuration to the ``ApiBackend``, use the ``Config`` class:

.. code-block:: python

   from lwe import ApiBackend
   from lwe.core.config import Config

   config = Config()
   config.set('debug.log.enabled', True)
   # You may also stream the response as it comes in from the API by
   # setting the model.streaming attribute.
   config.set('model.streaming', True)
   bot = ApiBackend(config)
   success, response, message = bot.ask("Hello, world!")
   if success:
       print(response)
   else:
       raise RuntimeError(message)


-----------------------------------------------
GPT-4
-----------------------------------------------

To use GPT-4 within your Python code, you must use :ref:`presets_doc`.

The code below uses the system-defined ``gpt-4-chatbot-responses`` preset:

.. code-block:: python

   from lwe import ApiBackend
   from lwe.core.config import Config

   config = Config()
   config.set('model.default_preset', 'gpt-4-chatbot-responses')
   bot = ApiBackend(config)
   success, response, message = bot.ask("Hello, world!")
