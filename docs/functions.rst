===============================================
Functions
===============================================


**NOTE: Alpha, subject to change**

The wrapper supports `OpenAI functions <https://platform.openai.com/docs/guides/gpt/function-calling>`_ for all models that support it.

Mutiple functions may be attached, and the LLM can choose to call any or all of the attached functions.

The example configuration below assumes you want to add a new function called ``test_function``.


-----------------------------------------------
Creating functions.
-----------------------------------------------

Functions are created as callable Python classes, that inherit from the base ``Function`` class.

The class name must be the camel-cased version of the snake-cased function name, so ``test_function`` becomes ``TestFunction``.

There is one required method to implement, ``__call__``, and its return value must be a dictionary -- this is what will be
returned to the LLM as the result of the function call.

.. code-block:: python

   from lwe.core.function import Function

   class TestFunction(Function):
       def __call__(self, word: str, repeats: int, enclose_with: str = '') -> dict:
           """
           Repeat the provided word a number of times.

           :param word: The word to repeat.
           :type content: str
           :param repeats: The number of times to repeat the word.
           :type repeats: int
           :param enclose_with: Optional string to enclose the final content.
           :type enclose_with: str, optional
           :return: A dictionary containing the repeated content.
           :rtype: dict
           """
           try:
               repeated_content = " ".join([word] * repeats)
               enclosed_content = f"{enclose_with}{repeated_content}{enclose_with}"
               output = {
                   'result': enclosed_content,
                   'message': f'Repeated the word {word} {repeats} times.',
               }
           except Exception as e:
               output = {
                   'error': str(e),
               }
           return output

The file should be named ``[function_name].py``, e.g. ``test_function.py``, and be placed in the ``functions`` directory
in either the base config directory, or in the profile config directory. (These directories are listed in the output
of the ``/config`` command).


-----------------------------------------------
Providing the function definition
-----------------------------------------------

In the example above, notice both the `type hints <https://docs.python.org/3/library/typing.html>`_ in the function signature (e.g. ``word: str``),
and the `reStructured text <https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html>`_ documentation of the method arguments.
This is the default method for providing the function definition to the OpenAI API.

Alternatively, you may provide the function definition by creating a ``[function_name].config.yaml`` file in the same location as the
``[function_name].py`` file, e.g. ``test_function.config.yaml`` -- if provided, its contents will be used instead of the default
method.

Finally, for full control, you may override the ``get_config()`` method of the base ``Function`` class, and return
a dictionary of the function definition.


-----------------------------------------------
Attaching functions.
-----------------------------------------------

For now, the function list must be attached to one of the existing :ref:`presets_doc`, as a list of function names, like so:

.. code-block:: yaml

   metadata:
     name: gpt-4-function-test
     provider: chat_openai
     # Add this to have the FIRST function CALL response from the LLM returned directly.
     # return_on_function_call: true
     # Add this to have the LAST function RESPONSE from the LLM returned directly.
     # return_on_function_response: true
   model_customizations:
     # Other attributes.
     model_name: gpt-4
     model_kwargs:
       # Functions are added under this key, as a list of function names.
       # Multiple functions can be added.
       functions:
         - test_function

A preset can be edited by using the ``/preset-edit`` command:

Note the special ``return_on_function_call`` and ``return_on_function_response`` metadata attributes, which can be used to
control the return value, useful when using the ``ApiBackend`` module, or via :ref:`workflows_doc`.


-----------------------------------------------
Support for Langchain tools
-----------------------------------------------

`Langchain <https://docs.langchain.com>`_ has many useful `tools <https://python.langchain.com/docs/modules/agents/tools/>`_
that can be used in function calls.

To use a Langchain tool as function:

#. Find the name of the tool class, e.g. ``MoveFileTool`` or ``ShellTool``.
#. Prefix that class name with ``Langchain-``
#. Add it to the ``functions`` list for the preset:

    .. code-block:: yaml

      metadata:
        # Usual preset metadata.
      model_customizations:
        # Other attributes.
        model_kwargs:
          functions:
            - Langchain-ShellTool
