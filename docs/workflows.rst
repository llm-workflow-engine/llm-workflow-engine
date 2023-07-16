.. _workflows_doc:

===============================================
Workflows
===============================================

LWE supports more complex linear workflows via built-in integration for `Ansible playbooks <https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_intro.html>`_.

If you chose to install the example workflows, you can run ``/workflows`` to list them, and ``/workflow-show workflowname`` to view the playbook configuration for a particular workflow.

To execute a workflow from within the program:

.. code-block:: console

   /workflow-run workflowname

To run a workflow from the command line:

.. code-block:: bash

   lwe --workflow workflowname

Calls to the LLM during workflows can either be run ad hoc (not saved to the database), or associated with a conversation stored in the database.

See ``/help`` for the various other workflow commands.


-----------------------------------------------
Building workflows
-----------------------------------------------

Workflows are, at their heart, `Ansible playbooks <https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_intro.html>`_.

If you're familiar with Ansible playbooks, you should find it trivial to build your own workflows.

If you have little or no experience with Ansible, fear not -- with a little work, mastering the needed Ansible skills is easy.

LWE also has a basic workflow for generating workflows in natural language, see :ref:`LLM workflow generation`


-----------------------------------------------
Custom Ansible modules/actions
-----------------------------------------------

LWE implements some custom modules and actions, which are described briefly below. These addtional modules and actions provide a bridge between the LLM and the other tasks in the workflow.


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Modules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``lwe_llm``: Handles communicating with the LLM and storing the response for each task execution. For supported arguments and return values, see the `lwe_llm module documentation <https://github.com/llm-workflow-engine/llm-workflow-engine/blob/main/lwe/backends/api/workflow/library/lwe_llm.py>`_.

Example:

.. code-block:: yaml

   - name: "Ask a question about blah"
     lwe_llm:
       preset: "{{ preset }}"
       user: "{{ user_id }}"
       system_message: "You are an expert at blah"
       message: "Tell me the three most important things about blah"
     register: response
     until: "response is not failed"
     retries: 10
     delay: 3

``text_extractor``: Provides an easy way to extract text content from many different file types. For supported arguments and return values, see the `text_extractor module documentation <https://github.com/llm-workflow-engine/llm-workflow-engine/blob/main/lwe/backends/api/workflow/library/text_extractor.py>`_.

Example:

.. code-block:: yaml

   - name: "Extract text from file: /tmp/foo.pdf"
     text_extractor:
       path: "/tmp/foo.pdf"
       max_length: 4000
     register: extracted_text


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Actions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``lwe_input``: Provides support for user input during a workflow, with some extra features beyond the default Ansible methods. For supported arguments and return values, see the `lwe_input action documentation <https://github.com/llm-workflow-engine/llm-workflow-engine/blob/main/lwe/backends/api/workflow/action_plugins/lwe_input.py>`_.

Example:

.. code-block:: yaml

   - name: Give next instructions
     lwe_input:
       prompt: "Please provide the next instructions"
     register: next_instructions


-----------------------------------------------
LLM workflow generation
-----------------------------------------------

LWE provides a few default templates that can assist you in building workflows using natural language. By leveraging these templates, you can have an LLM do most of the work of generating a workflow for you.

**NOTE:** While this process is very helpful and can get you most of the way there with writing a workflow, it's not guaranteed to output perfect working code -- you may still need to troubleshoot a few things to get it working. The `Ansible module documentation <https://docs.ansible.com/ansible/latest/collections/index_module.html>`_ can be extremely helpful in this situation!

Here's how to use the templates to generate workflows:

#. Start a new conversation

   .. code-block:: console

      /new

#. Generate a workflow spec based on your goals. At this point the goal is NOT to generate the final workflow, but instead to generate a specification that the LLM can use later as a complete reference for building the workflow.

   .. code-block:: console

      /template-edit-run workflow-spec-generator.md

   This opens the template in your editor. Under the ``GOAL`` section, describe the goal you're trying to accomplish. Try to be fairly specific -- the more detail you can give the LLM, the better it will be at producing the spec.

   Save and close the editor to run the template.

   After the LLM generates the initial spec, you can look it over, and if necessary, engage in a process of interative improvement with the LLM until it produces the spec you want.

#. Copy your original goal and the spec writtin by the LLM, you'll need them again shortly.

#. Start a new conversation

   .. code-block:: console

      /new

#. Generate the workflow based on the goal and the previous spec produced by the LLM.

   .. code-block:: console

      /template-edit-run workflow-generator.md

   Paste your original goal and the spec written by the LLM into the appropriate sections in the template, save and close the editor to run the template.

   If needed, you can engage in an iterative process of improvement with the LLM until the workflow is complete.

#. Copy the generated workflow code.

#. Create your new workflow(s)

   .. code-block:: console

      /workflow-edit workflowname

   Then paste in the generated workflow.

   It's possible that the LLM produced more than one workflow file, such that one file is 'included' in the other file. If this is the case, create one workflow per generated file, making sure to name the workflow appropriately based on how it's included  -- e.g., if it was included with ``include_tasks: foo.yaml``, you would name the 'include' workflow ``foo``.

#. Run workflow

   .. code-block:: console

      /workflow-run workflowname

At this point the workflow should either just work, or you may need to do a little troubleshooting to work out the last kinks.

-----------------------------------------------
Running Ansible playbooks directly
-----------------------------------------------

It is also possible to execute workflows directly with ``ansible-playbook``, by simply navigating to the ``lwe/backends/api/workflow`` directory and running:

.. code-block:: bash

   ansible-playbook </path/to/workflow.yaml>
