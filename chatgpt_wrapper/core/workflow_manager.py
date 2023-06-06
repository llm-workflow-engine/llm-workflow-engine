import os
import sys
import subprocess
import copy
import yaml
import getpass
import shlex

from chatgpt_wrapper.core.config import Config
from chatgpt_wrapper.core.logger import Logger
import chatgpt_wrapper.core.util as util

class WorkflowManager():
    """
    Manage workflows.
    """

    def __init__(self, config=None):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.workflow_dirs = self.make_workflow_dirs()
        self.create_runner_dir()
        self.load_workflows()

    def create_runner_dir(self):
        runner_dir = self.get_runner_dir()
        if not os.path.exists(runner_dir):
            os.makedirs(runner_dir)
        runner_env_dir = os.path.join(runner_dir, 'env')
        if not os.path.exists(runner_env_dir):
            os.makedirs(runner_env_dir)
            # Ansible Runner creates these files dynamically and fills them with values
            # from the first run.
            # We don't want this, so provide our own empty files.
            for file in ['envvars', 'extravars']:
                with open(os.path.join(runner_env_dir, file), 'w') as f:
                    f.write('{}')

    def get_workflow_dir(self):
        package_root = util.get_package_root(self)
        workflow_dir = os.path.join(package_root, 'backends', 'api', 'workflow')
        return workflow_dir

    def get_runner_dir(self):
        runner_dir = os.path.join(self.config.data_profile_dir, 'ansible-runner')
        return runner_dir

    def ensure_workflow(self, workflow_name):
        if not workflow_name:
            return False, None, "No workflow name specified"
        self.log.debug(f"Ensuring workflow {workflow_name} exists")
        if workflow_name not in self.workflows:
            self.load_workflows()
        if workflow_name not in self.workflows:
            return False, workflow_name, f"Workflow '{workflow_name}' not found"
        message = f"Workflow {workflow_name} exists"
        self.log.debug(message)
        return True, self.workflows[workflow_name], message

    def make_workflow_dirs(self):
        workflow_dir = self.get_workflow_dir()
        core_workflow_dir = os.path.join(workflow_dir, 'playbooks')
        workflow_dirs = []
        workflow_dirs.append(os.path.join(self.config.config_profile_dir, 'workflows'))
        workflow_dirs.append(os.path.join(self.config.config_dir, 'workflows'))
        workflow_dirs.append(core_workflow_dir)
        for workflow_dir in workflow_dirs:
            if not os.path.exists(workflow_dir):
                os.makedirs(workflow_dir)
        return workflow_dirs

    def get_workflow_environment_config(self):
        workflow_dir = self.get_workflow_dir()
        return {
            'ANSIBLE_PYTHON_INTERPRETER': {
                'op': 'add-if-empty',
                'default': sys.executable
            },
            'ANSIBLE_CONFIG': {
                'op': 'add-if-empty',
                'default': os.path.join(workflow_dir, 'ansible.cfg'),
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
            if data['op'] == 'add-if-empty':
                if not os.getenv(var):
                    self.log.debug(f"Setting workflow environment variable {var}: {data['default']}")
                    os.environ[var] = data['default']

    def parse_workflow_args(self, args_string):
        args_list = shlex.split(args_string)
        final_args = []
        for arg in args_list:
            key, value = arg.split('=', maxsplit=1)
            final_args.append("%s='%s'" % (key, value.replace("'", "\\'")))
        if final_args:
            return ' '.join(final_args)
        return ""

    def run(self, workflow_name, workflow_args):
        self.set_workflow_environment()
        success, workflow_file, message = self.ensure_workflow(workflow_name)
        if not success:
            return success, workflow_file, message
        self.log.info(f"Running workflow {workflow_name} from {workflow_file} with args: {workflow_args}")
        env = copy.copy(dict(os.environ))
        kwargs = {
            'env': env,
            'stdin': sys.stdin,
            'stdout': sys.stdout,
            'stderr': sys.stderr,
            'universal_newlines': True,
        }
        command = [
            'ansible-playbook',
            workflow_file,
        ]
        args = self.parse_workflow_args(workflow_args)
        if args:
            command = command + ['--extra-vars', args]

        return_code = 1
        error = "Unknown error"
        try:
            proc = subprocess.Popen(command, **kwargs)
            return_code = proc.wait()
        except Exception as e:
            error = e.message if hasattr(e, 'message') else str(e)
        if return_code == 0:
            return True, None, f"Workflow {workflow_name} completed"
        message = f"Error running workflow {workflow_name}: {error}"
        self.log.error(message)
        return False, None, message

    def load_workflows(self):
        self.log.debug("Loading workflows from dirs: %s" % ", ".join(self.workflow_dirs))
        self.workflows = {}
        try:
            for workflow_dir in self.workflow_dirs:
                if os.path.exists(workflow_dir) and os.path.isdir(workflow_dir):
                    self.log.info(f"Processing directory: {workflow_dir}")
                    for file_name in os.listdir(workflow_dir):
                        if file_name.endswith('.yaml') or file_name.endswith('.yml'):
                            workflow_name = os.path.splitext(file_name)[0]
                            workflow_file = os.path.join(workflow_dir, file_name)
                            self.workflows[workflow_name] = workflow_file
                else:
                    message = f"Failed to load workflows: Directory '{workflow_dir}' not found or not a directory"
                    self.log.error(message)
                    return False, None, message
            return True, self.workflows, "Workflows successfully loaded"
        except Exception as e:
            message = f"An error occurred while loading workflows: {e}"
            self.log.error(message)
            return False, None, message

    def delete_workflow(self, workflow_name, workflow_dir=None):
        success, workflow_file, user_message = self.ensure_workflow(workflow_name)
        if not success:
            return success, workflow_file, user_message
        try:
            os.remove(workflow_file)
            message = f"Successfully deleted workflow '{workflow_name}' from '{workflow_file}'"
            self.log.info(message)
            return True, workflow_name, message
        except Exception as e:
            message = f"An error occurred while deleting workflow '{workflow_name}': {e}"
            self.log.error(message)
            return False, None, message
