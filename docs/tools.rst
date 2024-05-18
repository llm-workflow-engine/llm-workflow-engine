===============================================
Tools
===============================================


LWE supports tools for providers that support them, such as `OpenAI <https://platform.openai.com/docs/guides/function-calling>`_.

Mutiple tools may be attached, and the LLM can choose to call any or all of the attached tools.

The example configuration below assumes you want to add a new tool called ``test_tool``.


-----------------------------------------------
Creating tools.
-----------------------------------------------

Tools are created as callable Python classes, that inherit from the base ``Tool`` class.

The class name must be the camel-cased version of the snake-cased tool name, so ``test_tool`` becomes ``TestTool``.

There is one required method to implement, ``__call__``, and its return value must be a dictionary -- this is what will be
returned to the LLM as the result of the tool call.

.. code-block:: python

   from lwe.core.tool import Tool

   class TestTool(Tool):
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

The file should be named ``[tool_name].py``, e.g. ``test_tool.py``, and be placed in the ``tools`` directory
in either the base config directory, or in the profile config directory. (These directories are listed in the output
of the ``/config`` command).


-----------------------------------------------
Providing the tool definition
-----------------------------------------------

In the example above, notice both the `type hints <https://docs.python.org/3/library/typing.html>`_ in the tool signature (e.g. ``word: str``),
and the `reStructured text <https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html>`_ documentation of the method arguments.
This is the default method for providing the tool definition to the model.

Alternatively, you may provide the tool definition by creating a ``[tool_name].config.yaml`` file in the same location as the
``[tool_name].py`` file, e.g. ``test_tool.config.yaml`` -- if provided, its contents will be used instead of the default
method.

Finally, for full control, you may override the ``get_config()`` method of the base ``Tool`` class, and return
a dictionary of the tool definition. This approach allows passing much more robust tool definitions to the LLM -- check out the
example tools provided with the project for an example of overriding ``get_config()`` using `Pydantic <https://docs.pydantic.dev/latest/>`_ schemas.


-----------------------------------------------
Attaching tools.
-----------------------------------------------

For now, the tool list must be attached to one of the existing :ref:`presets_doc`, as a list of tool names, like so:

.. code-block:: yaml

   metadata:
     name: gpt-4-tool-test
     provider: chat_openai
     # Add this to have the FIRST tool CALL response from the LLM returned directly.
     # return_on_tool_call: true
     # Add this to have the LAST tool RESPONSE from the LLM returned directly.
     # return_on_tool_response: true
   model_customizations:
     model_name: gpt-4o
     # Tools are added under this key, as a list of tool names.
     # Multiple tools can be added.
     tools:
       - test_tool
     # Optional: choice of tool to use
     # Can be the name of the tool, or one of the following special values:
     #   auto, none, any, required
     # NOTE: Not all providers support this, and supported providers don't all support all special values.
     # See the `Langchain tool calling documentation <https://python.langchain.com/docs/modules/model_io/chat/function_calling/#request-forcing-a-tool-call>`_ for more info.
     tool_choice: any

A preset can be edited by using the ``/preset-edit`` command:

Note the special ``return_on_tool_call`` and ``return_on_tool_response`` metadata attributes, which can be used to
control the return value, useful when using the ``ApiBackend`` module, or via :ref:`workflows_doc`.


-----------------------------------------------
Support for Langchain tools
-----------------------------------------------

`Langchain <https://docs.langchain.com>`_ has many useful `tools <https://python.langchain.com/docs/integrations/tools/>`_
that can be used in tool calls.

To use a Langchain tool:

#. Find the name of the tool class, e.g. ``MoveFileTool`` or ``ShellTool``.
#. Prefix that class name with ``Langchain-``
#. Add it to the ``tools`` list for the preset:

    .. code-block:: yaml

      metadata:
        # Usual preset metadata.
      model_customizations:
        tools:
          - Langchain-ShellTool
