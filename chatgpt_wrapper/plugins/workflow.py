import os

from chatgpt_wrapper.core.workflow_manager import WorkflowManager
from chatgpt_wrapper.core.plugin import Plugin
import chatgpt_wrapper.core.util as util

class Workflow(Plugin):

    def incompatible_backends(self):
        return [
            'browser',
        ]

    def default_config(self):
        return {
        }

    def setup(self):
        self.log.info("Setting up workflow plugin")
        self.workflow_manager = WorkflowManager(self.config, self.backend)
        self.workflow_manager.load_workflows()

    def get_shell_completions(self, _base_shell_completions):
        commands = {}
        commands[util.command_with_leader('workflow-run')] = util.list_to_completion_hash(self.workflow_manager.workflows.keys())
        commands[util.command_with_leader('workflows')] = None
        return commands

    def do_workflow_run(self, args):
        """
        Run a workflow

        Arguments:
            workflow_name: Required. The name of the workflow
            additional_args: Any additional arguments to pass to the workflow

        Examples:
            {COMMAND} myworkflow
        """
        if not args:
            return False, args, "No workflow name specified"
        try:
            workflow_name, workflow_args = args.split(" ", 1)[0], args.split(" ", 1)[1]
        except IndexError:
            workflow_name = args.strip()
            workflow_args = ""
        try:
            success, result, user_message = self.workflow_manager.run(workflow_name, workflow_args)
            return success, result, user_message
        except Exception as e:
            return False, None, f"Error running workflow {workflow_name}: {e}"

    def do_workflows(self, arg):
        """
        List available workflows

        Workflows enable multi-step interaction with LLMs, with simple decision-making
        abilities.

        They are located in the 'workflows' directory in the following locations:

            - The core workflows directory
            - The main configuration directory
            - The profile configuration directory

        See {COMMAND_LEADER}config for current locations of the configuration and
        profile directories.

        Arguments:
            filter_string: Optional. If provided, only workflows with a name or description containing the filter string will be shown.

        Examples:
            {COMMAND}
            {COMMAND} filterstring
        """
        self.workflow_manager.load_workflows()
        self.shell.rebuild_completions()
        workflows = []
        for workflow_name in self.workflow_manager.workflows.keys():
            content = f"* **{workflow_name}**"
            if not arg or arg.lower() in content.lower():
                workflows.append(content)
        util.print_markdown("## Workflows:\n\n%s" % "\n".join(sorted(workflows)))
