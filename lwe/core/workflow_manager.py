import os
import sys
import subprocess
import shutil
import copy
import shlex
import yaml

from lwe.core.config import Config
from lwe.core.logger import Logger
import lwe.core.util as util


class WorkflowManager:
    """
    Manage workflows.
    """

    def __init__(self, config=None):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.user_workflow_dirs = (
            self.config.args.workflows_dir
            or util.get_environment_variable_list("workflow_dir")
            or self.config.get("directories.workflows")
        )
        self.make_user_workflow_dirs()
        self.system_workflow_dirs = [
            os.path.join(util.get_package_root(self), "workflows"),
        ]
        self.all_workflow_dirs = self.system_workflow_dirs + self.user_workflow_dirs
        self.load_workflows()

    def get_workflow_dir(self):
        package_root = util.get_package_root(self)
        workflow_dir = os.path.join(package_root, "backends", "api", "workflow")
        return workflow_dir

    def ensure_workflow(self, workflow_name):
        if not workflow_name:
            return False, None, "No workflow name specified"
        self.log.debug(f"Ensuring workflow {workflow_name} exists")
        if workflow_name not in self.workflows:
            self.load_workflows()
        if workflow_name not in self.workflows:
            return False, workflow_name, f"Workflow {workflow_name!r} not found"
        message = f"Workflow {workflow_name} exists"
        self.log.debug(message)
        return True, self.workflows[workflow_name], message

    def ensure_runnable_workflow(self, workflow_name):
        success, workflow, user_message = self.load_workflow(workflow_name)
        if not success:
            return success, workflow, user_message
        if len(workflow) > 0:
            if "tasks" in workflow[0]:
                return True, workflow, f"Workflow {workflow_name!r} has a valid play with tasks"
            return (
                False,
                workflow,
                f"Workflow {workflow_name!r} has no tasks, are you trying to run an 'include' file?",
            )
        return False, workflow, f"Workflow {workflow_name!r} has invalid format"

    def make_user_workflow_dirs(self):
        for workflow_dir in self.user_workflow_dirs:
            if not os.path.exists(workflow_dir):
                os.makedirs(workflow_dir)

    def get_workflow_environment_config(self):
        workflow_dir = self.get_workflow_dir()
        return {
            "ANSIBLE_PYTHON_INTERPRETER": {"op": "add-if-empty", "default": sys.executable},
            "ANSIBLE_CONFIG": {
                "op": "add-if-empty",
                "default": os.path.join(workflow_dir, "ansible.cfg"),
            },
            # 'ANSIBLE_STDOUT_CALLBACK': {
            #     'op': 'add-if-empty',
            #     'default': 'community.general.yaml',
            # },
            # 'ANSIBLE_LIBRARY': {
            #     'op': 'append',
            #     'default': os.path.join(workflow_dir, 'library'),
            # },
            # 'ANSIBLE_ROLES_PATH': {
            #     'op': 'add-if-empty',
            #     'default': os.path.join(workflow_dir, 'roles'),
            # },
            # 'ANSIBLE_ROLES_PATH': {
            #     'op': 'add-if-empty',
            #     'default': os.path.join(workflow_dir, 'roles'),
            # },
            # 'ANSIBLE_PLAYBOOK_DIR': {
            #     'op': 'add-if-empty',
            #     'default': os.path.join(workflow_dir, 'playbooks'),
            # },
        }

    def set_workflow_environment(self):
        for var, data in self.get_workflow_environment_config().items():
            if data["op"] == "add-if-empty":
                if not os.getenv(var):
                    self.log.debug(
                        f"Setting workflow environment variable {var}: {data['default']}"
                    )
                    os.environ[var] = data["default"]

    def parse_workflow_args(self, args_string):
        args_list = shlex.split(args_string)
        final_args = []
        for arg in args_list:
            key, value = arg.split("=", maxsplit=1)
            final_args.append("%s='%s'" % (key, value.replace("'", "\\'")))
        if final_args:
            return " ".join(final_args)
        return ""

    def run(self, workflow_name, workflow_args):
        success, _, user_message = self.ensure_runnable_workflow(workflow_name)
        if not success:
            return success, workflow_name, user_message
        self.set_workflow_environment()
        success, workflow_file, message = self.ensure_workflow(workflow_name)
        if not success:
            return success, workflow_file, message
        self.log.info(
            f"Running workflow {workflow_name} from {workflow_file} with args: {workflow_args}"
        )
        env = copy.copy(dict(os.environ))
        kwargs = {
            "env": env,
            "stdin": sys.stdin,
            "stdout": sys.stdout,
            "stderr": sys.stderr,
            "universal_newlines": True,
        }
        command = [
            "ansible-playbook",
            workflow_file,
        ]
        args = self.parse_workflow_args(workflow_args)
        if args:
            command = command + ["--extra-vars", args]

        return_code = 1
        error = "Unknown error"
        try:
            proc = subprocess.Popen(command, **kwargs)
            return_code = proc.wait()
        except Exception as e:
            error = e.message if hasattr(e, "message") else str(e)
        if return_code == 0:
            return True, None, f"Workflow {workflow_name} completed"
        message = f"Error running workflow {workflow_name}: {error}"
        self.log.error(message)
        return False, None, message

    def load_workflow(self, workflow_name):
        success, workflow_file, message = self.ensure_workflow(workflow_name)
        if not success:
            return success, workflow_file, message
        self.log.info(f"Loading workflow {workflow_name} from {workflow_file}")
        try:
            with open(workflow_file, "r") as f:
                workflow = yaml.safe_load(f)
            return True, workflow, f"Workflow {workflow_name} successfully loaded"
        except Exception as e:
            message = f"An error occurred while loading workflow {workflow_name}: {e}"
            self.log.error(message)
            return False, None, message

    def load_workflows(self):
        self.log.debug("Loading workflows from dirs: %s" % ", ".join(self.all_workflow_dirs))
        self.workflows = {}
        try:
            for workflow_dir in self.all_workflow_dirs:
                if os.path.exists(workflow_dir) and os.path.isdir(workflow_dir):
                    self.log.info(f"Processing directory: {workflow_dir}")
                    for file_name in os.listdir(workflow_dir):
                        if file_name.endswith(".yaml") or file_name.endswith(".yml"):
                            workflow_name = os.path.splitext(file_name)[0]
                            workflow_file = os.path.join(workflow_dir, file_name)
                            self.workflows[workflow_name] = workflow_file
                else:
                    message = f"Failed to load workflows: Directory {workflow_dir!r} not found or not a directory"
                    self.log.error(message)
                    return False, None, message
            return True, self.workflows, "Workflows successfully loaded"
        except Exception as e:
            message = f"An error occurred while loading workflows: {e}"
            self.log.error(message)
            return False, None, message

    def copy_workflow(self, old_name, new_name):
        """
        Copies a workflow file to a new location.

        :param old_name: The name of the existing workflow file.
        :type old_name: str
        :param new_name: The name for the new workflow file.
        :type new_name: str
        :return: A tuple containing a boolean indicating success or failure, the new file path, and a status message.
        :rtype: tuple
        """
        success, workflow_file, user_message = self.ensure_workflow(old_name)
        if not success:
            return success, workflow_file, user_message
        old_filepath = workflow_file
        base_filepath = (
            self.user_workflow_dirs[-1]
            if self.is_system_workflow(old_filepath)
            else os.path.dirname(old_filepath)
        )
        if not new_name.endswith(".yaml") and not new_name.endswith(".yml"):
            new_name += ".yaml"
        new_filepath = os.path.join(base_filepath, new_name)
        if os.path.exists(new_filepath):
            return False, new_filepath, f"{new_filepath} already exists"
        shutil.copy2(old_filepath, new_filepath)
        self.load_workflows()
        return True, new_filepath, f"Copied workflow {old_filepath} to {new_filepath}"

    def delete_workflow(self, workflow_name, workflow_dir=None):
        success, workflow_file, user_message = self.ensure_workflow(workflow_name)
        if not success:
            return success, workflow_file, user_message
        try:
            os.remove(workflow_file)
            message = f"Successfully deleted workflow {workflow_name!r} from {workflow_file!r}"
            self.log.info(message)
            return True, workflow_name, message
        except Exception as e:
            message = f"An error occurred while deleting workflow {workflow_name!r}: {e}"
            self.log.error(message)
            return False, None, message

    def is_system_workflow(self, filepath):
        for dir in self.system_workflow_dirs:
            if filepath.startswith(dir):
                return True
        return False
