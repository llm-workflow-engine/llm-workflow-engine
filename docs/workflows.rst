.. _workflows_doc:

===============================================
Workflows
===============================================

**NOTE: Alpha, subject to change**

The wrapper supports more complex linear workflows via built-in integration for `Ansible playbooks <https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_intro.html>`_.

Some example workflows are included, run ``/workflows`` to list them, and ``/workflow-show workflowname`` to view the playbook configuration for a particular workflow.

To execute a workflow, run ``/workflow-run workflowname`` -- depending on configuration, workflows can either be run ad hoc (not saved to the database), or associated with a conversation stored in the database.

See ``/help`` for the various other workflow commands.

The wrapper implements a custom Ansible module, ``lwe_llm``, which handles communicating with the LLM and storing the response for each task execution. For supported arguments and return values, see the `module documentation <https://github.com/llm-workflow-engine/llm-workflow-engine/blob/main/lwe/backends/api/workflow/library/lwe_llm.py>`_.

It is also possible to execute workflows directly with ``ansible-playbook``, by simply navigating to the ``lwe/backends/api/workflow`` directory:

.. code-block:: bash

   ansible-playbook playbooks/hello-world.yaml
