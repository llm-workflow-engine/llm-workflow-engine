import os
import sys
import yaml
import getpass
import shlex

import ansible_runner

from chatgpt_wrapper.core.config import Config
from chatgpt_wrapper.core.logger import Logger
import chatgpt_wrapper.core.util as util

def parse_workflow_dict(content):
    metadata = {}
    customizations = {}
    for key, value in content.items():
        if key.startswith('_'):
            metadata[key[1:]] = value
        else:
            customizations[key] = value
    return metadata, customizations

class WorkflowManager():
    """
    Manage workflows.
    """

    def __init__(self, config=None, backend=None):
        self.config = config or Config()
        self.backend = backend
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
        package_root = util.get_package_root(self)
        core_workflow_dir = os.path.join(package_root, 'backends', 'api', 'workflow', 'playbooks')
        workflow_dirs = []
        workflow_dirs.append(os.path.join(self.config.config_profile_dir, 'workflows'))
        workflow_dirs.append(os.path.join(self.config.config_dir, 'workflows'))
        workflow_dirs.append(core_workflow_dir)
        for workflow_dir in workflow_dirs:
            if not os.path.exists(workflow_dir):
                os.makedirs(workflow_dir)
        return workflow_dirs

    def merge_workflow_config(self, workflow_instance):
        config_key = f"workflows.{workflow_instance.name}"
        default_config = workflow_instance.default_config()
        user_config = self.config.get(config_key) or {}
        self.log.debug(f"Merging workflow {config_key} config, default: {default_config}, user: {user_config}")
        workflow_config = util.merge_dicts(default_config, user_config)
        self.config.set(config_key, workflow_config)

    def setup_workflow(self, workflow_name, workflow_instance):
        workflow_instance.set_name(workflow_name)
        workflow_instance.set_backend(self.backend)
        self.merge_workflow_config(workflow_instance)
        workflow_instance.setup()
        return True

    def get_workflow_environment_config(self):
        package_root = util.get_package_root(self)
        workflow_dir = os.path.join(package_root, 'backends', 'api', 'workflow')
        return {
            'ANSIBLE_PYTHON_INTERPRETER': {
                'op': 'add-if-empty',
                'default': sys.executable
            },
            'ANSIBLE_CONFIG': {
                'op': 'add-if-empty',
                'default': os.path.join(workflow_dir, 'ansible.cfg'),
            },
            # Set here instead of in ansible.cfg because ansible-runner only allows
            # overriding this setting via an environment variable.
            'ANSIBLE_STDOUT_CALLBACK': {
                'op': 'add-if-empty',
                'default': 'community.general.yaml',
            },
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
        args_string = args_string.strip()
        if not args_string:
            return {}
        args_list = shlex.split(args_string)
        args_dict = {}
        for arg in args_list:
            key, value = arg.split('=')
            args_dict[key] = value
        return args_dict

    def collect_vars(self, workflow_file, workflow_args):
        self.log.debug(f"Collecting vars for {workflow_file} with args: {workflow_args}")
        final_vars = self.parse_workflow_args(workflow_args)
        with open(workflow_file, 'r') as file:
            playbook = yaml.safe_load(file)
        for play in playbook:
            if 'vars_prompt' in play:
                for prompt in play['vars_prompt']:
                    name = prompt.get('name')
                    prompt_text = prompt.get('prompt')
                    is_private = prompt.get('private', False)
                    if name not in final_vars:
                        if is_private:
                            user_input = getpass.getpass(prompt_text + " ")
                        else:
                            user_input = input(prompt_text + " ")
                        final_vars[name] = user_input
        self.log.debug(f"Collected vars for {workflow_file}: {final_vars}")
        return final_vars

    def run(self, workflow_name, workflow_args):
        self.set_workflow_environment()
        success, workflow_file, message = self.ensure_workflow(workflow_name)
        if not success:
            return success, workflow_file, message
        self.log.info(f"Running workflow {workflow_name} from {workflow_file} with args: {workflow_args}")
        try:
            collected_vars = self.collect_vars(workflow_file, workflow_args)
            envvars = dict(os.environ)
            result = ansible_runner.run(
                private_data_dir=self.get_runner_dir(),
                playbook=workflow_file,
                envvars=envvars,
                extravars=collected_vars,
                # json_mode=True,
            )
            # print("{}: {}".format(r.status, r.rc))
            # for each_host_event in r.events:
            #     print(each_host_event['event'])
            # print("Final status:")
            # print(r.stats)
            return True, result, f"Workflow {workflow_name} completed"
        except Exception as e:
            message = f"Error running workflow {workflow_name} from {workflow_file}: {e}"
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
