import os
import getpass
import yaml
import email_validator

import chatgpt_wrapper.core.constants as constants
import chatgpt_wrapper.core.util as util
from chatgpt_wrapper.core.repl import Repl
from chatgpt_wrapper.backends.api.database import Database
from chatgpt_wrapper.backends.api.orm import User
from chatgpt_wrapper.backends.api.user import UserManager
from chatgpt_wrapper.backends.api.backend import ApiBackend
from chatgpt_wrapper.core.editor import file_editor

ALLOWED_BASE_SHELL_NOT_LOGGED_IN_COMMANDS = [
    'config',
    'exit',
    'quit',
]
SKIP_MESSAGE = "(Press enter to skip)"

class ApiRepl(Repl):
    """
    A shell interpreter that serves as a front end to the ApiBackend class
    """

    def __init__(self, config=None):
        super().__init__(config)
        self.logged_in_user = None

    def not_logged_in_disallowed_commands(self):
        base_shell_commands = util.introspect_commands(Repl)
        disallowed_commands = [c for c in base_shell_commands if c not in ALLOWED_BASE_SHELL_NOT_LOGGED_IN_COMMANDS]
        return disallowed_commands

    def exec_prompt_pre(self, command, arg):
        if not self.logged_in_user and command in self.not_logged_in_disallowed_commands():
            return False, None, "Must be logged in to execute %s%s" % (constants.COMMAND_LEADER, command)

    def configure_shell_commands(self):
        self.commands = util.introspect_commands(__class__)

    def get_custom_shell_completions(self):
        user_commands = [
            'login',
            'user',
            'user-delete',
            'user-edit',
            'user-login',
        ]
        success, users, user_message = self.user_management.get_users()
        if not success:
            raise Exception(user_message)
        if users:
            usernames = [u.username for u in users]
            for command in user_commands:
                # Overwriting the commands directly, as merging still includes deleted users.
                self.base_shell_completions["%s%s" % (constants.COMMAND_LEADER, command)] = {username: None for username in usernames}
        self.base_shell_completions[util.command_with_leader('model')] = self.backend.provider.customizations_to_completions()
        provider_completions = {}
        for _name, provider in self.backend.get_providers().items():
            provider_models = util.list_to_completion_hash(provider.available_models) if provider.available_models else None
            provider_completions[provider.display_name()] = provider_models
        final_completions = {
            util.command_with_leader('system-message'): util.list_to_completion_hash(self.backend.get_system_message_aliases()),
            util.command_with_leader('provider'): provider_completions,
        }
        preset_keys = self.backend.preset_manager.presets.keys()
        for subcmd in ['save', 'load', 'delete', 'show']:
            final_completions[util.command_with_leader(f"preset-{subcmd}")] = util.list_to_completion_hash(preset_keys) if preset_keys else None
        for preset_name in preset_keys:
            final_completions[util.command_with_leader("preset-save")][preset_name] = util.list_to_completion_hash(self.backend.preset_manager.user_metadata_fields())
        final_completions[util.command_with_leader('workflows')] = None
        subcommands = [
            'run',
            'show',
            'edit',
            'delete',
        ]
        for subcommand in subcommands:
            final_completions[util.command_with_leader(f"workflow-{subcommand}")] = util.list_to_completion_hash(self.backend.workflow_manager.workflows.keys())
        return final_completions

    def configure_backend(self):
        self.backend = ApiBackend(self.config)
        database = Database(self.config)
        database.create_schema()
        self.user_management = UserManager(self.config)
        self.session = self.user_management.orm.session

    def launch_backend(self, interactive=True):
        if interactive:
            self.check_login()

    def get_user(self, user_id):
        user = self.session.get(User, user_id)
        return user

    def _is_logged_in(self):
        return self.logged_in_user is not None

    def validate_email(self, email):
        try:
            valid = email_validator.validate_email(email)
            return True, valid.email
        except email_validator.EmailNotValidError as e:
            return False, f"Invalid email: {e}"

    def select_preset(self, allow_empty=False):
        presets = list(self.backend.preset_manager.presets.keys())
        presets.insert(0, "Global default")
        for i, preset in enumerate(presets):
            print(f"{i + 1}. {preset}")
        selected_preset = input(f"Choose a default preset {SKIP_MESSAGE}: ").strip() or None
        if not selected_preset and allow_empty:
            return True, None
        if not selected_preset or not selected_preset.isdigit() or not (1 <= int(selected_preset) <= len(presets)):
            return False, "Invalid preset selection."
        if int(selected_preset) == 1:
            default_preset = ""
        else:
            default_preset = presets[int(selected_preset) - 1]
        return True, default_preset

    # Overriding default implementation because API should use UUIDs.
    def do_context(self, arg):
        """
        Load an old context from the log

        Arguments:
            context_string: a context string from logs

        Examples:
            {COMMAND} 67d1a04b-4cde-481e-843f-16fdb8fd3366:0244082e-8253-43f3-a00a-e2a82a33cba6
        """
        try:
            (conversation_id, parent_message_id) = arg.split(":")
            assert conversation_id == "None" or int(conversation_id) > 0
            assert int(parent_message_id) > 0
        except Exception:
            util.print_markdown("Invalid parameter to `context`.")
            return
        util.print_markdown("* Loaded specified context.")
        self.backend.conversation_id = (
            conversation_id if conversation_id != "None" else None
        )
        self.backend.parent_message_id = parent_message_id
        self._update_message_map()
        self._write_log_context()

    def do_user_register(self, username=None):
        """
        Register a new user

        If the 'username' argument is not provided, you will be prompted for it.

        You will also be prompted for:
            email: Optional, valid email
            password: Optional, if given will be required for login

        Arguments:
            username: The username of the new user

        Examples:
            {COMMAND}
            {COMMAND} myusername
        """
        if not username:
            username = input("Enter username (no spaces): ").strip() or None
            if not username:
                return False, None, "Username cannot be empty."
        email = input("Enter email: ").strip() or None
        if email:
            success, message = self.validate_email(email)
            if not success:
                return False, None, message
        password = getpass.getpass(prompt='Enter password (leave blank for passwordless login): ') or None
        # NOTE: Not sure if it's a good workflow to prompt for this on register,
        # leaving out for now.
        # success, default_preset = self.select_preset()
        # if not success:
        #     return False, None, "Invalid default preset."
        # success, user, user_message = self.user_management.register(username, email, password, default_preset)
        success, user, user_message = self.user_management.register(username, email, password)
        if success:
            self.rebuild_completions()
        return success, user, user_message


    def check_login(self):
        user_count = self.session.query(User).count()
        if user_count == 0:
            util.print_status_message(False, "No users in database. Creating one...")
            self.welcome_message()
            self.create_first_user()
        # Special case check: if there's only one user in the database, and
        # they have no password, log them in.
        elif user_count == 1:
            user = self.session.query(User).first()
            if not user.password:
                return self.login(user)

    def welcome_message(self):
        util.print_markdown(
"""
# Welcome to the ChatGPT API shell!

This shell interacts directly with the ChatGPT API, and stores conversations and messages in the configured database.

Before you can start using the shell, you must create a new user.
"""
        )

    def create_first_user(self):
        success, user, message = self.do_user_register()
        util.print_status_message(success, message)
        if success:
            success, _user, message = self.login(user)
            util.print_status_message(success, message)
        else:
            self.create_first_user()

    def build_shell_user_prefix(self):
        if not self.logged_in_user:
            return ''
        prompt_prefix = self.config.get("shell.prompt_prefix")
        prompt_prefix = prompt_prefix.replace("$USER", self.logged_in_user.username)
        prompt_prefix = prompt_prefix.replace("$MODEL", self.backend.model)
        prompt_prefix = prompt_prefix.replace("$PRESET_OR_MODEL", self.backend.active_preset if self.backend.active_preset else self.backend.model)
        prompt_prefix = prompt_prefix.replace("$NEWLINE", "\n")
        prompt_prefix = prompt_prefix.replace("$TEMPERATURE", self.get_model_temperature())
        prompt_prefix = prompt_prefix.replace("$MAX_SUBMISSION_TOKENS", str(self.backend.max_submission_tokens))
        conversation_tokens = "" if self.backend.conversation_tokens is None else str(self.backend.conversation_tokens)
        prompt_prefix = prompt_prefix.replace("$CURRENT_CONVERSATION_TOKENS", conversation_tokens)
        prompt_prefix = prompt_prefix.replace("$SYSTEM_MESSAGE_ALIAS", self.backend.system_message_alias or "")
        return f"{prompt_prefix} "

    def get_model_temperature(self):
        temperature = 'N/A'
        success, temperature, _user_message = self.backend.provider.get_customization_value('temperature')
        if success:
            temperature = temperature
        return str(temperature)

    def set_logged_in_user(self, user=None):
        self.logged_in_user = user
        self.backend.set_current_user(user)

    def login(self, user):
        if user.password:
            password = getpass.getpass(prompt='Enter password: ')
            success, user, message = self.user_management.login(user.username, password)
        else:
            success, user, message = True, user, "Login successful."
        if success:
            self.set_logged_in_user(user)
            self.backend.new_conversation()
        return success, user, message

    def do_user_login(self, identifier=None):
        """
        Login in as a user

        If the 'identifier' argument is not provided, you will be prompted for either a username or email.
        You will be prompted for a password if one is set for the user.

        Arguments:
            identifier: The username or email

        Examples:
            {COMMAND}
            {COMMAND} myusername
            {COMMAND} email@example.com
        """
        if not identifier:
            identifier = input("Enter username or email: ")
        success, user, message = self.user_management.get_by_username_or_email(identifier)
        if success:
            if user:
                return self.login(user)
            else:
                return False, user, message
        else:
            return success, user, message

    def do_login(self, identifier=None):
        """
        Alias of '{COMMAND_LEADER}user-login'

        Login in as a user.

        Arguments:
            identifier: The username or email

        Examples:
            {COMMAND}
            {COMMAND} myusername
            {COMMAND} email@example.com
        """
        return self.do_user_login(identifier)

    def do_user_logout(self, _):
        """
        Logout the current user.

        Examples:
            {COMMAND}
        """
        if not self._is_logged_in():
            return False, None, "Not logged in."
        self.set_logged_in_user()
        return True, None, "Logout successful."

    def do_logout(self, _):
        """
        Alias of '{COMMAND_LEADER}user-logout'

        Logout the current user.

        Examples:
            {COMMAND}
        """
        return self.do_user_logout(None)

    def display_user(self, user):
        output = """
## Username: %s

* Email: %s
* Password: %s
* Default preset: %s
        """ % (user.username, user.email, "set" if user.password else "Not set", user.default_preset if user.default_preset else "Global default")
        util.print_markdown(output)

    def do_user(self, username=None):
        """
        Show user information

        Arguments:
            username: The username of the user to show, if not provided, the logged in user will be used.

        Examples:
            {COMMAND}
            {COMMAND} ausername
        """
        if not self._is_logged_in():
            return False, None, "Not logged in."
        if username:
            success, user, message = self.user_management.get_by_username(username)
            if success:
                if user:
                    return self.display_user(user)
                else:
                    return False, user, message
            else:
                return success, user, message
        elif self.logged_in_user:
            return self.display_user(self.logged_in_user)
        return False, None, "User not found."

    def do_users(self, _):
        """
        Show information for all users

        Examples:
            {COMMAND}
        """
        success, users, message = self.user_management.get_users()
        if success:
            user_list = ["* %s: %s" % (user.id, user.username) for user in users]
            user_list.insert(0, "# Users")
            util.print_markdown("\n".join(user_list))
        else:
            return success, users, message

    def edit_user(self, user):
        util.print_markdown(f"## Editing user: {user.username}")
        username = input(f"New username {SKIP_MESSAGE}: ").strip() or None
        email = input(f"New email {SKIP_MESSAGE}: ").strip() or None
        if email:
            success, message = self.validate_email(email)
            if not success:
                return False, email, message
        password = getpass.getpass(prompt=f"New password {SKIP_MESSAGE}: ") or None
        success, default_preset = self.select_preset(True)
        if not success:
            return False, default_preset, "Invalid default preset."

        kwargs = {
            "username": username,
            "email": email,
            "password": password,
            "default_preset": default_preset,
        }
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        success, user, user_message = self.user_management.edit_user(user.id, **kwargs)
        if success:
            self.rebuild_completions()
            if self.logged_in_user.id == user.id:
                self.backend.set_current_user(user)
        return success, user, user_message

    def do_user_edit(self, username=None):
        """
        Edit the current user's information

        You will be prompted to enter new values for the username, email, password, and default model.
        You can skip any prompt by pressing enter.

        Examples:
            {COMMAND}
        """
        if not self._is_logged_in():
            return False, None, "Not logged in."
        if username:
            success, user, message = self.user_management.get_by_username(username)
            if not success:
                return success, user, message
            if user:
                return self.edit_user(user)
            else:
                return False, user, message
        elif self.logged_in_user:
            return self.edit_user(self.logged_in_user)
        return False, "User not found."

    def do_user_delete(self, username=None):
        """
        Delete a user

        If the 'username' argument is not provided, you will be prompted for it.
        The currently logged in user cannot be deleted.

        Arguments:
            username: The username of the user to be deleted

        Examples:
            {COMMAND}
            {COMMAND} myusername
        """
        if not self._is_logged_in():
            return False, None, "Not logged in."
        if not username:
            username = input("Enter username: ")
        success, user, message = self.user_management.get_by_username(username)
        if not success:
            return success, user, message
        if user:
            if user.id == self.logged_in_user.id:
                return False, user, "Cannot delete currently logged in user."
            else:
                success, user, user_message = self.user_management.delete_user(user.id)
                if success:
                    self.rebuild_completions()
                return success, user, user_message
        else:
            return False, user, message

    def get_set_backend_setting(self, value_type, setting, value, min=None, max=None):
        if value:
            method = getattr(util, f"validate_{value_type}")
            value = method(value, min, max)
            if value is False:
                valid_range = []
                if min is not None:
                    valid_range.append(f"greater than or equal to {min}")
                if max is not None:
                    valid_range.append(f"less than or equal to {max}")
                range_description = ": " + ", ".join(valid_range) if len(valid_range) > 0 else ""
                return False, value, f"Invalid {setting}, must be {value_type}{range_description}."
            else:
                method = getattr(self.backend, f"set_{setting}")
                return method(value)
        else:
            value = getattr(self.backend, setting)
            util.print_markdown(f"* Current {setting}: {value}")

    def do_system_message(self, alias=None):
        """
        Set the system message sent for conversations.

        The system message helps set the behavior of the assistant. Conversations begin with a system message to gently instruct the assistant.

        Arguments:
            system_message: String, {OPENAPI_MIN_SUBMISSION_TOKENS} to {OPENAPI_DEFAULT_MAX_SUBMISSION_TOKENS} characters long, or a system message alias name from the configuration.
                            The special string 'default' will reset the system message to its default value.
                            With no arguments, show the currently set system message.

        Examples:
            {COMMAND}
            {COMMAND} {SYSTEM_MESSAGE_DEFAULT}
        """
        if not self._is_logged_in():
            return False, None, "Not logged in."
        if alias:
            return self.backend.set_system_message(alias)
        else:
            aliases = self.backend.get_system_message_aliases()
            alias_list = []
            for alias in aliases.keys():
                alias_string = f"* {alias}"
                if alias == self.backend.system_message_alias:
                    alias_string += ' (✓)'
                alias_list.append(alias_string)
            output = "## System message:\n\n%s\n\n## Available aliases:\n\n%s" % (self.backend.system_message, "\n".join(alias_list))
            util.print_markdown(output)

    def do_max_submission_tokens(self, max_submission_tokens=None):
        """
        The maximum number of tokens that can be submitted to the model.

        For chat-based providers, this will be used to truncate earlier messages in the
        conversation to keep the total number of tokens within the set value.

        For non-chat-based providers, this value can only be viewed, if available.

        If the provider configuration specifies a max tokens value for a model, it will
        be used. Otherwise, a default value of {OPENAPI_MAX_TOKENS} will be used.

        Arguments:
            max_submission_tokens: An integer between {OPENAPI_MIN_SUBMISSION_TOKENS} and the
                                   maximum value a model can accept. (chat providers only)
            With no arguments, view the current max submission tokens.

        Examples:
            {COMMAND}
            {COMMAND} 256
        """
        return self.get_set_backend_setting("int", "max_submission_tokens", max_submission_tokens, min=constants.OPENAPI_MIN_SUBMISSION_TOKENS)

    def do_providers(self, arg):
        """
        List currently enabled providers

        Examples:
            {COMMAND}
        """
        self.rebuild_completions()
        provider_plugins = [f"* {provider.display_name()}" for provider in self.backend.provider_manager.provider_plugins.values()]
        util.print_markdown("## Providers:\n\n%s" % "\n".join(sorted(provider_plugins)))

    def do_provider(self, arg):
        """
        View or set the current LLM provider

        Arguments:
            provider: The name of the provider to set.
            model_name: Optional. The model to initialize the provider with.
            With no arguments, view current set model attributes

        Examples:
            {COMMAND}
            {COMMAND} chat_openai
            {COMMAND} chat_openai gpt-4
        """
        if arg:
            try:
                provider, model_name, *rest = arg.split()
                if rest:
                    return False, arg, "Too many parameters, should be 'provider model_name'"
            except ValueError:
                provider = arg
                model_name = None
            success, provider, user_message = self.backend.set_provider(provider)
            if success:
                if model_name:
                    self.backend.set_model(model_name)
                self.rebuild_completions()
            return success, provider, user_message
        else:
            return self.do_model('')

    def do_presets(self, arg):
        """
        List available presets

        Preset are pre-configured provider/model configurations that can be stored and loaded for convenience.

        They are located in the 'presets' directory in the following locations:

            - The main configuration directory
            - The profile configuration directory

        See {COMMAND_LEADER}config for current locations.

        Arguments:
            filter_string: Optional. If provided, only presets with a name or description containing the filter string will be shown.

        Examples:
            {COMMAND}
            {COMMAND} filterstring
        """
        self.backend.preset_manager.load_presets()
        self.rebuild_completions()
        presets = []
        for preset_name, data in self.backend.preset_manager.presets.items():
            metadata, _customizations = data
            content = f"* **{preset_name}**"
            if 'description' in metadata:
                content += f": *{metadata['description']}*"
            if preset_name == self.backend.active_preset:
                content += ' (✓)'
            if not arg or arg.lower() in content.lower():
                presets.append(content)
        util.print_markdown("## Presets:\n\n%s" % "\n".join(sorted(presets)))

    def do_preset_show(self, preset_name):
        """
        Display a preset

        Arguments:
            preset_name: Required. The name of the preset

        Examples:
            {COMMAND} mypreset
        """
        success, preset, user_message = self.backend.preset_manager.ensure_preset(preset_name)
        if not success:
            return success, preset, user_message
        metadata, customizations = preset
        util.print_markdown(f"\n## Preset '{preset_name}'")
        util.print_markdown("### Model customizations\n```yaml\n%s\n```" % yaml.dump(customizations, default_flow_style=False))
        util.print_markdown("### Metadata\n```yaml\n%s\n```" % yaml.dump(metadata, default_flow_style=False))

    def do_preset_save(self, args):
        """
        Create a new preset, or update an existing preset

        Arguments:
            preset_name: Required. The name of the preset
            [metadata_field]: Optional. The name of a metadata field, followed by the value
                Valid metadata fields are:
                    description: A description of the preset
                    system_message: A system message to activate for the preset,
                                    can be a configured alias or a custom message

        Examples:
            {COMMAND} mypreset
        """
        if not args:
            return False, args, "No preset name specified"
        extra_metadata = {}
        success, existing_preset, user_message = self.backend.preset_manager.ensure_preset(args.split()[0])
        if success:
            existing_metadata, _customizations = existing_preset
            for key in self.backend.preset_manager.user_metadata_fields():
                if key in existing_metadata:
                    extra_metadata[key] = existing_metadata[key]
        metadata, customizations = self.backend.make_preset()
        try:
            preset_name, metadata_field, *rest = args.split()
            if metadata_field not in self.backend.preset_manager.user_metadata_fields():
                return False, metadata_field, f"Invalid metadata field: {metadata_field}"
            extra_metadata[metadata_field] = " ".join(rest)
        except ValueError:
            preset_name = args
        metadata.update(extra_metadata)
        success, file_path, user_message = self.backend.preset_manager.save_preset(preset_name, metadata, customizations)
        if success:
            self.backend.preset_manager.load_presets()
            success, preset, load_preset_message = self.do_preset_load(preset_name)
            if not success:
                return success, preset, load_preset_message
        return success, file_path, user_message

    def do_preset_load(self, preset_name):
        """
        Load an existing preset

        This activates the provider and model customizations stored in the preset as the current
        configuration.

        Arguments:
            preset_name: Required. The name of the preset to load.

        Examples:
            {COMMAND} mypreset
        """
        success, preset, user_message = self.backend.activate_preset(preset_name)
        if success:
            self.rebuild_completions()
        return success, preset, user_message

    def do_preset_delete(self, preset_name):
        """
        Deletes an existing preset

        Arguments:
            preset_name: Required. The name of the preset to delete

        Examples:
            {COMMAND} mypreset
        """
        success, preset, user_message = self.backend.preset_manager.ensure_preset(preset_name)
        if not success:
            return success, preset, user_message
        success, _, user_message = self.backend.preset_manager.delete_preset(preset_name)
        if success:
            self.backend.preset_manager.load_presets()
            if self.backend.active_preset == preset_name:
                self.backend.init_provider()
            self.rebuild_completions()
        return success, preset_name, user_message

    def do_workflows(self, arg):
        """
        List available workflows

        Workflows enable multi-step interaction with LLMs, with simple decision-making
        abilities.

        They are located in the 'workflows' directory in the following locations, and
        searched in this order:

            - The profile configuration directory
            - The main configuration directory
            - The core workflows directory

        See {COMMAND_LEADER}config for current locations of the configuration and
        profile directories.

        Arguments:
            filter_string: Optional. If provided, only workflows with a name or description containing the filter string will be shown.

        Examples:
            {COMMAND}
            {COMMAND} filterstring
        """
        self.backend.workflow_manager.load_workflows()
        self.rebuild_completions()
        workflows = []
        for workflow_name in self.backend.workflow_manager.workflows.keys():
            content = f"* **{workflow_name}**"
            if not arg or arg.lower() in content.lower():
                workflows.append(content)
        util.print_markdown("## Workflows:\n\n%s" % "\n".join(sorted(workflows)))

    def do_workflow_run(self, args):
        """
        Run a workflow

        Arguments:
            workflow_name: Required. The name of the workflow
            variables: Space-separated list of additional variables to pass to the workflow

        Examples:
            {COMMAND} myworkflow
            {COMMAND} myworkflow foo=bar baz="bang bong"
        """
        if not args:
            return False, args, "No workflow name specified"
        try:
            workflow_name, workflow_args = args.split(" ", 1)[0], args.split(" ", 1)[1]
        except IndexError:
            workflow_name = args.strip()
            workflow_args = ""
        success, result, user_message = self.backend.workflow_manager.run(workflow_name, workflow_args)
        return success, result, user_message

    def do_workflow_show(self, workflow_name):
        """
        Display a workflow

        Arguments:
            workflow_name: Required. The name of the workflow

        Examples:
            {COMMAND} myworkflow
        """
        if not workflow_name:
            return False, None, "No workflow name specified"
        success, workflow_file, user_message = self.backend.workflow_manager.ensure_workflow(workflow_name)
        if not success:
            return success, workflow_file, user_message
        with open(workflow_file) as f:
            workflow_content = f.read()
        util.print_markdown(f"\n## Workflow '{workflow_name}'")
        util.print_markdown("```yaml\n%s\n```" % workflow_content)

    def do_workflow_edit(self, workflow_name):
        """
        Create a new workflow, or edit an existing workflow

        Arguments:
            workflow_name: Required. The name of the workflow

        Examples:
            {COMMAND} myworkflow
        """
        if not workflow_name:
            return False, workflow_name, "No workflow name specified"
        success, workflow_file, user_message = self.backend.workflow_manager.ensure_workflow(workflow_name)
        if success:
            filename = workflow_file
        else:
            workflow_name = f"{workflow_name}.yaml" if not workflow_name.endswith('.yaml') else workflow_name
            filename = os.path.join(self.backend.workflow_manager.workflow_dirs[0], workflow_name)
        file_editor(filename)
        self.backend.workflow_manager.load_workflows()
        self.rebuild_completions()

    def do_workflow_delete(self, workflow_name):
        """
        Deletes an existing workflow

        Arguments:
            workflow_name: Required. The name of the workflow to delete

        Examples:
            {COMMAND} myworkflow
        """
        if not workflow_name:
            return False, None, "No workflow name specified"
        success, workflow_name, user_message = self.backend.workflow_manager.delete_workflow(workflow_name)
        if success:
            self.backend.workflow_manager.load_workflows()
            self.rebuild_completions()
        return success, workflow_name, user_message
