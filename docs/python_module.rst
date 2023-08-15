.. _python_module_doc:

===============================================
Python module
===============================================

You can  use the ``ApiBackend`` class to interact directly with the LLMs.

Create an instance of the class and use the ``ask`` method to send a message to the LLM and receive the response. For example:

.. code-block:: python

   from lwe import ApiBackend

   bot = ApiBackend()
   success, response, message = bot.ask("Say hello!")
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
   bot = ApiBackend(config)
   success, response, message = bot.ask("Say hello!")
   if success:
       print(response)
   else:
       raise RuntimeError(message)

To stream a response:

#. Define a callback function to receive streaming chunks
#. Define a ``request_overrides`` dict, passing the defined callback in the ``stream_callback`` key
#. Pass ``request_overrides`` as an argument to the ``ask_stream`` method


.. code-block:: python

  from lwe import ApiBackend

  def stream_callback(content):
      print(content, end='', flush=True)

  bot = ApiBackend()
  request_overrides = {
      'stream_callback': stream_callback
  }
  success, response, message = bot.ask_stream("Say three words about earth", request_overrides=request_overrides)


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


-----------------------------------------------
Advanced Python module usage
-----------------------------------------------

The ``ApiBackend`` class has full access to most of the features available in the LWE shell:

* Templates
* Presets
* Workflows
* OpenAI functions
* etc...

If you're a moderately skilled Python programmer, you should be able to figure out how to
make use of these features using the ``ApiBackend`` class by looking at the
:ref:`core shell module <lwe.core.repl module>` and :ref:`API shell module <lwe.backends.api.repl module>` code,
or examining the documentation for :ref:`ApiBackend <lwe.backends.api.backend module>`.
