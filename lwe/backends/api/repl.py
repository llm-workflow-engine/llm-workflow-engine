import os
import getpass
import yaml
import email_validator

import lwe.core.constants as constants
import lwe.core.util as util
from lwe.core.repl import Repl
from lwe.backends.api.orm import User
from lwe.backends.api.user import UserManager
from lwe.backends.api.backend import ApiBackend
from lwe.core.editor import file_editor

ALLOWED_BASE_SHELL_NOT_LOGGED_IN_COMMANDS = [
    "config",
    "exit",
    "quit",
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
        disallowed_commands = [
            c for c in base_shell_commands if c not in ALLOWED_BASE_SHELL_NOT_LOGGED_IN_COMMANDS
        ]
        return disallowed_commands

    def exec_prompt_pre(self, command, arg):
        if not self.logged_in_user and command in self.not_logged_in_disallowed_commands():
            return (
                False,
                None,
                "Must be logged in to execute %s%s" % (constants.COMMAND_LEADER, command),
            )

    def configure_shell_commands(self):
        self.commands = util.introspect_commands(__class__)

    def get_custom_shell_completions(self):
        user_commands = sorted(self.get_command_actions("user", dashed=True))
        success, users, user_message = self.user_management.get_users()
        if not success:
            raise Exception(user_message)
        usernames = {u.username: None for u in users} if users else None
        # Overwriting the commands directly, as merging still includes deleted users.
        self.base_shell_completions[util.command_with_leader("user")] = {
            c: None if c == "logout" else usernames for c in user_commands
        }
        self.base_shell_completions[util.command_with_leader("model")] = (
            self.backend.provider.customizations_to_completions()
        )
        provider_completions = {}
        for _name, provider in self.backend.get_providers().items():
            provider_models = (
                util.list_to_completion_hash(provider.available_models)
                if provider.available_models
                else None
            )
            provider_completions[provider.display_name] = provider_models
        final_completions = {
            util.command_with_leader("system-message"): util.list_to_completion_hash(
                self.backend.get_system_message_aliases()
            ),
            util.command_with_leader("provider"): provider_completions,
        }
        preset_keys = self.backend.preset_manager.presets.keys()
        final_completions[util.command_with_leader("preset")] = {
            c: util.list_to_completion_hash(preset_keys)
            for c in self.get_command_actions("preset", dashed=True)
        }
        for preset_name in preset_keys:
            final_completions[util.command_with_leader("preset")]["save"][preset_name] = (
                util.list_to_completion_hash(
                    self.backend.preset_manager.user_metadata_fields().keys()
                )
            )
        workflow_keys = util.list_to_completion_hash(self.backend.workflow_manager.workflows.keys())
        final_completions[util.command_with_leader("workflow")] = {
            c: workflow_keys for c in self.get_command_actions("workflow", dashed=True)
        }
        return final_completions

    def configure_backend(self):
        if not getattr(self, "backend", None):
            self.backend = ApiBackend(self.config)
        self.user_management = UserManager(self.config, self.backend.orm)

    def launch_backend(self, interactive=True):
        if interactive:
            self.check_login()

    def get_user(self, user_id):
        return self.user_management.get_by_user_id(user_id)

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
        if (
            not selected_preset
            or not selected_preset.isdigit()
            or not (1 <= int(selected_preset) <= len(presets))
        ):
            return False, "Invalid preset selection."
        if int(selected_preset) == 1:
            default_preset = ""
        else:
            default_preset = presets[int(selected_preset) - 1]
        return True, default_preset

    # Overriding default implementation because API should use UUIDs.
    # def command_context(self, arg):
    #     """
    #     Load an old context from the log

    #     Arguments:
    #         context_string: a context string from logs

    #     Examples:
    #         {COMMAND} 67d1a04b-4cde-481e-843f-16fdb8fd3366:0244082e-8253-43f3-a00a-e2a82a33cba6
    #     """
    #     try:
    #         conversation_id = arg
    #         assert conversation_id == "None" or int(conversation_id) > 0
    #     except Exception:
    #         util.print_markdown("Invalid parameter to `context`.")
    #         return
    #     util.print_markdown("* Loaded specified context.")
    #     self.backend.conversation_id = (
    #         conversation_id if conversation_id != "None" else None
    #     )
    #     self._update_message_map()
    #     self._write_log_context()

    def action_user_register(self, username=None):
        """
        Register a new user

        If the 'username' argument is not provided, you will be prompted for it.

        You will also be prompted for:
            email: Optional, valid email
            password: Optional, if given will be required for login

        :param username: The username of the new user
        :type username: str

        :return: A tuple containing the success status, user object, and a message
        :rtype: tuple[bool, User, str]
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
        password = (
            getpass.getpass(prompt="Enter password (leave blank for passwordless login): ") or None
        )
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
        """
        Check if a user is logged in

        :return: None
        """
        user_count = self.user_management.session.query(User).count()
        if user_count == 0:
            util.print_status_message(False, "No users in database. Creating one...")
            self.welcome_message()
            self.create_first_user()
        # Special case check: if there's only one user in the database, and
        # they have no password, log them in.
        elif user_count == 1:
            user = self.user_management.session.query(User).first()
            if not user.password:
                return self.login(user)

    def welcome_message(self):
        """
        Print the welcome message

        :return: None
        """
        util.print_markdown(
            """
# Welcome to the LLM Workflow Engine shell!

This shell interacts directly with ChatGPT and other LLMs via their API, and stores conversations and messages in the configured database.

Before you can start using the shell, you must create a new user.
"""
        )

    def add_examples(self):
        """
        Add example configurations

        :return: None
        """
        if "examples" in self.backend.plugin_manager.plugins:
            from lwe.plugins.examples import TYPES as example_types

            examples = self.backend.plugin_manager.plugins["examples"]
            confirmation = input(
                f"Would you like to install example configurations for: {', '.join(example_types)}? [y/N] "
            ).strip()
            if confirmation.lower() in ["yes", "y"]:
                examples.install_examples()

    def create_first_user(self):
        """
        Create the first user

        :return: None
        """
        success, user, message = self.action_user_register()
        util.print_status_message(success, message)
        if success:
            success, _user, message = self.login(user)
            util.print_status_message(success, message)
            self.add_examples()
        else:
            self.create_first_user()

    def get_current_conversation_title(self):
        """
        Get the title of the current conversation

        :return: The title of the current conversation
        :rtype: str
        """
        if self.backend.conversation_id:
            conversation_title = self.backend.get_current_conversation_title()
            if conversation_title:
                title = conversation_title[: constants.SHORT_TITLE_LENGTH]
                if len(conversation_title) > constants.SHORT_TITLE_LENGTH:
                    title += "..."
            else:
                title = constants.UNTITLED_CONVERSATION
        else:
            title = constants.NEW_CONVERSATION_TITLE
        return title

    def build_shell_user_prefix(self):
        """
        Build the prefix for the shell prompt

        :return: The prefix for the shell prompt
        :rtype: str
        """
        if not self.logged_in_user:
            return ""
        prompt_prefix = self.config.get("shell.prompt_prefix")
        prompt_prefix = prompt_prefix.replace("$TITLE", self.get_current_conversation_title())
        prompt_prefix = prompt_prefix.replace("$USER", self.logged_in_user.username)
        prompt_prefix = prompt_prefix.replace("$MODEL", self.backend.model)
        prompt_prefix = prompt_prefix.replace(
            "$PRESET_OR_MODEL",
            (
                self.backend.active_preset_name
                if self.backend.active_preset_name
                else self.backend.model
            ),
        )
        prompt_prefix = prompt_prefix.replace("$NEWLINE", "\n")
        prompt_prefix = prompt_prefix.replace("$TEMPERATURE", self.get_model_temperature())
        prompt_prefix = prompt_prefix.replace(
            "$MAX_SUBMISSION_TOKENS", str(self.backend.max_submission_tokens)
        )
        conversation_tokens = (
            ""
            if self.backend.conversation_tokens is None
            else str(self.backend.conversation_tokens)
        )
        prompt_prefix = prompt_prefix.replace("$CURRENT_CONVERSATION_TOKENS", conversation_tokens)
        prompt_prefix = prompt_prefix.replace(
            "$SYSTEM_MESSAGE_ALIAS", self.backend.system_message_alias or ""
        )
        return f"{prompt_prefix} "

    def get_model_temperature(self):
        """
        Get the temperature of the model

        :return: The temperature of the model
        :rtype: str
        """
        temperature = "N/A"
        success, temperature, _user_message = self.backend.provider.get_customization_value(
            "temperature"
        )
        if success:
            temperature = temperature
        return str(temperature)

    def set_logged_in_user(self, user=None):
        """
        Set the logged in user

        :param user: The user object to set as the logged in user
        :type user: User

        :return: None
        """
        self.logged_in_user = user
        self.backend.set_current_user(user)

    def command_user(self, args):
        """
        Run actions on users

        Available actions:
            * delete: Delete a user
            * edit: Edit a user
            * login: Log in a user
            * logout: Log out a user
            * register: Register a new user
            * show: Show a user

        Arguments:
            user_name: Optional, will be prompted for if necessary, defaults to currently logged in user

            When registering, you can optionally supply email/password -- no password is passwordless login.

            Login can be username or email.

        Examples:
            * {COMMAND} delete [myuser]
            * {COMMAND} edit [myuser]
            * {COMMAND} login [myuser]
            * {COMMAND} logout
            * {COMMAND} register [myuser]
            * {COMMAND} show [myuser]
        """
        return self.dispatch_command_action("user", args)

    def login(self, user):
        """
        Log in as a user

        :param user: The user to log in as
        :type user: User

        :return: A tuple containing the success status, user object, and a message
        :rtype: tuple[bool, User, str]
        """
        if user.password:
            password = getpass.getpass(prompt="Enter password: ")
            success, user, message = self.user_management.login(user.username, password)
        else:
            success, user, message = True, user, "Login successful."
        if success:
            self.set_logged_in_user(user)
            self.backend.new_conversation()
        return success, user, message

    def action_user_login(self, identifier=None):
        """
        Login in as a user

        If the 'identifier' argument is not provided, you will be prompted for either a username or email.
        You will be prompted for a password if one is set for the user.

        :param identifier: The username or email
        :type identifier: str

        :return: A tuple containing the success status, user object, and a message
        :rtype: tuple[bool, User, str]
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

    def command_login(self, identifier=None):
        """
        Alias of '{COMMAND_LEADER}user-login'

        Login in as a user.

        :param identifier: The username or email
        :type identifier: str

        :return: The result of the action_user_login method
        :rtype: Any
        """
        return self.action_user_login(identifier)

    def action_user_logout(self):
        """
        Logout the current user.

        :return: A tuple containing the success status, None, and a message
        :rtype: tuple[bool, None, str]
        """
        if not self._is_logged_in():
            return False, None, "Not logged in."
        self.set_logged_in_user()
        return True, None, "Logout successful."

    def command_logout(self, _):
        """
        Alias of '{COMMAND_LEADER}user-logout'

        Logout the current user.

        :param _: Unused argument

        :return: The result of the action_user_logout method
        :rtype: Any
        """
        return self.action_user_logout()

    def display_user(self, user):
        """
        Display user information

        :param user: The user object to display information for
        :type user: User

        :return: None
        """
        output = """
## Username: %s

* Email: %s
* Password: %s
* Default preset: %s
        """ % (
            user.username,
            user.email,
            "set" if user.password else "Not set",
            user.default_preset if user.default_preset else "Global default",
        )
        util.print_markdown(output)

    def action_user_show(self, username=None):
        """
        Show user information

        :param username: The username of the user to show, if not provided, the logged in user will be used.
        :type username: str

        :return: The result of the display_user method
        :rtype: Any
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

    def command_users(self, _):
        """
        Show information for all users

        :param _: Unused argument

        :return: The result of the user_management.get_users method
        :rtype: Any
        """
        success, users, message = self.user_management.get_users()
        if success:
            user_list = ["* %s: %s" % (user.id, user.username) for user in users]
            user_list.insert(0, "# Users")
            util.print_markdown("\n".join(user_list))
        else:
            return success, users, message

    def edit_user(self, user):
        """
        Edit user information

        :param user: The user object to edit
        :type user: User

        :return: A tuple containing the success status, user object, and a message
        :rtype: tuple[bool, User, str]
        """
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

    def action_user_edit(self, username=None):
        """
        Edit the current user's information

        :param username: The username of the user to edit, if not provided, the logged in user will be used.
        :type username: str

        :return: The result of the edit_user method
        :rtype: Any
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

    def action_user_delete(self, username=None):
        """
        Delete a user

        :param username: The username of the user to be deleted
        :type username: str

        :return: A tuple containing the success status, user object, and a message
        :rtype: tuple[bool, User, str]
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

    def command_system_message(self, alias=None):
        """
        Set the system message sent for conversations.

        The system message helps set the behavior of the assistant. Conversations begin with a system message to gently instruct the assistant.

        Arguments:
            system_message: String, or a system message alias name from the configuration.
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
                    alias_string += f" {constants.ACTIVE_ITEM_INDICATOR}"
                alias_list.append(alias_string)
            output = "## System message:\n\n%s\n\n## Available aliases:\n\n%s" % (
                self.backend.system_message,
                "\n".join(sorted(alias_list)),
            )
            util.print_markdown(output)

    def command_max_submission_tokens(self, max_submission_tokens=None):
        """
        The maximum number of tokens that can be submitted to the model.

        For chat-based providers, this will be used to truncate earlier messages in the
        conversation to keep the total number of tokens within the set value.

        For non-chat-based providers, this value can only be viewed, if available.

        If the provider configuration specifies a max tokens value for a model, it will
        be used. Otherwise, a default value of {OPEN_AI_MAX_TOKENS} will be used.

        Arguments:
            max_submission_tokens: An integer between {OPEN_AI_MIN_SUBMISSION_TOKENS} and the maximum value a model can accept. (chat providers only)

        With no arguments, view the current max submission tokens.

        Examples:
            {COMMAND}
            {COMMAND} 256
        """
        return self.get_set_backend_setting(
            "int",
            "max_submission_tokens",
            max_submission_tokens,
            min=constants.OPEN_AI_MIN_SUBMISSION_TOKENS,
        )

    def command_providers(self, arg):
        """
        List currently enabled providers

        Examples:
            {COMMAND}
        """
        self.rebuild_completions()
        provider_plugins = [
            f"* {provider.display_name}"
            for provider in self.backend.provider_manager.provider_plugins.values()
        ]
        util.print_markdown("## Providers:\n\n%s" % "\n".join(sorted(provider_plugins)))

    def command_provider(self, arg):
        """
        View or set the current LLM provider

        Arguments:
            provider: The name of the provider to set.
            model_name: Optional. The model to initialize the provider with.
            With no arguments, view current set model attributes

        Examples:
            {COMMAND}
            {COMMAND} chat_openai
            {COMMAND} chat_openai gpt-4o
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
                    success, model, user_message = self.backend.set_model(model_name)
            self.rebuild_completions()
            return success, provider, user_message
        else:
            return self.command_model("")

    def command_presets(self, arg):
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
        success, presets, user_message = self.backend.preset_manager.load_presets()
        if not success:
            return success, presets, user_message
        self.rebuild_completions()
        preset_names = []
        for preset_name, data in presets.items():
            metadata, _customizations = data
            content = f"* **{preset_name}**"
            if "description" in metadata:
                content += f": *{metadata['description']}*"
            if preset_name == self.backend.active_preset_name:
                content += f" {constants.ACTIVE_ITEM_INDICATOR}"
            if not arg or arg.lower() in content.lower():
                preset_names.append(content)
        util.print_markdown("## Presets:\n\n%s" % "\n".join(sorted(preset_names)))

    def command_preset(self, args):
        """
        Run actions on presets

        Presets are saved provider/model configurations.

        Available actions:
            * delete: Delete a preset
            * load: Load a preset (makes it the active preset)
            * edit: Open a preset for editing
            * save: Save the existing configuration to a preset, and/or set metadata on the preset
            * show: Show a preset

        Arguments:
            preset_name: Required. The name of the preset.

        Examples:
            * /preset delete mypreset
            * /preset load mypreset
            * /preset edit mypreset
            * /preset save mypreset
            * /preset save mypreset description This is my description
            * /preset save mypreset system_message Speak like a pirate
            * /preset save mypreset max_submission_tokens 4000
            * /preset save mypreset return_on_tool_call true
            * /preset save mypreset return_on_tool_response true
            * /preset save mypreset max_submission_tokens (without value, setting is deleted)
            * /preset show mypreset
        """
        return self.dispatch_command_action("preset", args)

    def action_preset_show(self, preset_name=None):
        """
        Display a preset

        :param preset_name: Optional. The name of the preset to show (default: active preset)
        :type preset_name: str

        :return: A tuple containing the success status, the preset, and a user message
        :rtype: tuple
        """
        if not preset_name:
            if not self.backend.active_preset_name:
                return False, None, "No active preset"
            preset_name = self.backend.active_preset_name
        success, preset, user_message = self.backend.preset_manager.ensure_preset(preset_name)
        if not success:
            return success, preset, user_message
        metadata, customizations = preset
        util.print_markdown(f"\n## Preset {preset_name!r}")
        util.print_markdown(
            "### Model customizations\n```yaml\n%s\n```"
            % yaml.dump(customizations, default_flow_style=False)
        )
        util.print_markdown(
            "### Metadata\n```yaml\n%s\n```" % yaml.dump(metadata, default_flow_style=False)
        )

    def action_preset_save(self, *args):
        """
        Create a new preset, or update an existing preset

        :param args: The arguments passed to the method, first must be the preset name,
                     second is the metadata name, and others are the metadata value to be saved
        :type args: tuple

        :return: A tuple containing the success status, the preset, and a user message
        :rtype: tuple
        """
        args = list(args)
        if not args:
            return False, args, "No preset name specified"
        preset_name = args.pop(0)
        extra_metadata = {}
        success, existing_preset, user_message = self.backend.preset_manager.ensure_preset(
            preset_name
        )
        user_metadata_fields = self.backend.preset_manager.user_metadata_fields()
        if success:
            existing_metadata, _customizations = existing_preset
            if self.backend.preset_manager.is_system_preset(existing_metadata["filepath"]):
                return (
                    False,
                    args,
                    f"{existing_metadata['name']} is a system preset, and cannot be edited directly",
                )
            for key in user_metadata_fields.keys():
                if key in existing_metadata:
                    extra_metadata[key] = existing_metadata[key]
        metadata, customizations = self.backend.make_preset()
        if args:
            metadata_field, *rest = args
            if metadata_field not in user_metadata_fields.keys():
                return False, metadata_field, f"Invalid metadata field: {metadata_field}"
            if not rest:
                del extra_metadata[metadata_field]
            else:
                if user_metadata_fields[metadata_field] is bool:
                    if rest[0].lower() in ["true", "yes", "y", "1"]:
                        extra_metadata[metadata_field] = True
                    else:
                        extra_metadata[metadata_field] = False
                elif user_metadata_fields[metadata_field] is int:
                    extra_metadata[metadata_field] = int(rest[0])
                else:
                    extra_metadata[metadata_field] = " ".join(rest)
        metadata.update(extra_metadata)
        success, file_path, user_message = self.backend.preset_manager.save_preset(
            preset_name, metadata, customizations
        )
        if success:
            success, presets, user_message = self.backend.preset_manager.load_presets()
            if not success:
                return success, presets, user_message
            success, preset, load_preset_message = self.action_preset_load(preset_name)
            if not success:
                return success, preset, load_preset_message
        return success, file_path, user_message

    def action_preset_edit(self, preset_name=None):
        """
        Edit an existing preset

        :param preset_name: Required. The name of the preset
        :type preset_name: str

        :return: A tuple containing the success status, the preset name, and a user message
        :rtype: tuple
        """
        if not preset_name:
            return False, preset_name, "No preset name specified"
        success, preset, user_message = self.backend.preset_manager.ensure_preset(preset_name)
        if success:
            metadata, _customizations = preset
            if self.backend.preset_manager.is_system_preset(metadata["filepath"]):
                return (
                    False,
                    preset_name,
                    f"{metadata['name']} is a system preset, and cannot be edited directly",
                )
        else:
            return success, preset_name, user_message
        file_editor(metadata["filepath"])
        success, presets, user_message = self.backend.preset_manager.load_presets()
        if not success:
            return success, presets, user_message
        if self.backend.active_preset_name == preset_name:
            success, preset, user_message = self.backend.activate_preset(preset_name)
            if success:
                return success, preset, f"Edited and re-actived preset: {preset_name}"
            return success, preset, user_message
        return True, preset_name, f"Edited preset: {preset_name}"

    def action_preset_load(self, preset_name=None):
        """
        Load an existing preset

        This activates the provider and model customizations stored in the preset as the current
        configuration.

        :param preset_name: Required. The name of the preset to load.
        :type preset_name: str

        :return: A tuple containing the success status, the preset, and a user message
        :rtype: tuple
        """
        if not preset_name:
            return False, preset_name, "No preset name specified"
        success, preset, user_message = self.backend.activate_preset(preset_name)
        if success:
            self.rebuild_completions()
        return success, preset, user_message

    def action_preset_delete(self, preset_name=None):
        """
        Deletes an existing preset

        :param preset_name: Required. The name of the preset to delete
        :type preset_name: str

        :return: A tuple containing the success status, the preset name, and a user message
        :rtype: tuple
        """
        if not preset_name:
            return False, preset_name, "No preset name specified"
        success, preset, user_message = self.backend.preset_manager.ensure_preset(preset_name)
        if success:
            metadata, _customizations = preset
            if self.backend.preset_manager.is_system_preset(metadata["filepath"]):
                return (
                    False,
                    preset_name,
                    f"{metadata['name']} is a system preset, and cannot be deleted",
                )
        else:
            return success, preset, user_message
        confirmation = input(
            f"Are you sure you want to delete preset {preset_name}? [y/N] "
        ).strip()
        if confirmation.lower() in ["yes", "y"]:
            success, _, user_message = self.backend.preset_manager.delete_preset(preset_name)
            if success:
                success, _presets, user_message = self.backend.preset_manager.load_presets()
                if success:
                    if self.backend.active_preset_name == preset_name:
                        self.backend.init_provider()
                    self.rebuild_completions()
            return success, preset_name, user_message
        else:
            return False, preset_name, "Deletion aborted"

    def command_workflows(self, arg):
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
        include_files = []
        for workflow_name in self.backend.workflow_manager.workflows.keys():
            success, workflow, user_message = self.backend.workflow_manager.load_workflow(
                workflow_name
            )
            if not success:
                return success, None, user_message
            if len(workflow) > 0:
                content = f"* **{workflow_name}**"
                if "tasks" in workflow[0]:
                    name_parts = []
                    for p in workflow:
                        if "name" in p:
                            name_parts.append(p["name"])
                    content += ": *%s*" % ", ".join(name_parts)
                    if not arg or arg.lower() in content.lower():
                        workflows.append(content)
                else:
                    if not arg or arg.lower() in content.lower():
                        include_files.append(content)
        util.print_markdown(
            "## Workflows:\n\n%s\n\n## Include files:\n\n%s"
            % ("\n".join(sorted(workflows)), "\n".join(sorted(include_files)))
        )

    def command_workflow(self, args):
        """
        Run actions on workflows

        Workflows enable multi-step interaction with LLMs, with simple decision-making
        abilities.

        Available actions:
            * copy: Copy a workflow
            * delete: Delete a workflow
            * edit: Open or create a workflow for editing
            * run: Run a workflow
            * show: Show a workflow

        Arguments:
            workflow_name: Required. The name of the workflow.

            For copy, a new workflow name is also required.

            For run, arguments may be supplied in key=value format, these will override
            default vars in the workflow.

        Examples:
            * /workflow copy myworkflow myworkflow_copy
            * /workflow delete myworkflow
            * /workflow edit myworkflow
            * /workflow run myworkflow
            * /workflow run myworkflow argument="some value"
            * /workflow show myworkflow
        """
        return self.dispatch_command_action("workflow", args)

    def action_workflow_run(self, *args):
        """
        Run a workflow

        Arguments:
            workflow_name: Required. The name of the workflow
            variables: Space-separated list of additional variables to pass to the workflow

        Examples:
            {COMMAND} myworkflow
            {COMMAND} myworkflow foo=bar baz="bang bong"
        """
        args = list(args)
        if not args:
            return False, args, "No workflow name specified"
        workflow_name = args.pop(0)
        workflow_args = " ".join(args)
        success, result, user_message = self.backend.workflow_manager.run(
            workflow_name, workflow_args
        )
        return success, result, user_message

    def action_workflow_show(self, workflow_name=None):
        """
        Display a workflow

        Arguments:
            workflow_name: Required. The name of the workflow

        Examples:
            {COMMAND} myworkflow
        """
        if not workflow_name:
            return False, None, "No workflow name specified"
        success, workflow_file, user_message = self.backend.workflow_manager.ensure_workflow(
            workflow_name
        )
        if not success:
            return success, workflow_file, user_message
        with open(workflow_file) as f:
            workflow_content = f.read()
        util.print_markdown(f"\n## Workflow {workflow_name!r}")
        util.print_markdown("```yaml\n%s\n```" % workflow_content)

    def action_workflow_copy(self, *workflow_names):
        """
        Copies an existing workflow and saves it as a new workflow

        Arguments:
            workflow_names: Required. The name of the old and new workflows separated by whitespace,

        Examples:
            {COMMAND} old_workflow new_workflow
        """
        try:
            old_name, new_name = workflow_names
        except ValueError:
            return False, workflow_names, "Old and new workflow name required"

        success, new_filepath, user_message = self.backend.workflow_manager.copy_workflow(
            old_name, new_name
        )
        if not success:
            return success, new_filepath, user_message
        self.rebuild_completions()
        return True, new_filepath, f"Copied {old_name} to {new_filepath}"

    def action_workflow_edit(self, workflow_name=None):
        """
        Create a new workflow, or edit an existing workflow

        Arguments:
            workflow_name: Required. The name of the workflow

        Examples:
            {COMMAND} myworkflow
        """
        if not workflow_name:
            return False, workflow_name, "No workflow name specified"
        success, workflow_file, user_message = self.backend.workflow_manager.ensure_workflow(
            workflow_name
        )
        if success:
            filename = workflow_file
            if self.backend.workflow_manager.is_system_workflow(filename):
                return (
                    False,
                    workflow_name,
                    f"{workflow_name} is a system workflow, and cannot be edited directly",
                )
        else:
            workflow_name = (
                f"{workflow_name}.yaml" if not workflow_name.endswith(".yaml") else workflow_name
            )
            filename = os.path.join(
                self.backend.workflow_manager.user_workflow_dirs[-1], workflow_name
            )
        file_editor(filename)
        self.backend.workflow_manager.load_workflows()
        self.rebuild_completions()

    def action_workflow_delete(self, workflow_name=None):
        """
        Deletes an existing workflow

        Arguments:
            workflow_name: Required. The name of the workflow to delete

        Examples:
            {COMMAND} myworkflow
        """
        if not workflow_name:
            return False, None, "No workflow name specified"
        success, workflow_file, user_message = self.backend.workflow_manager.ensure_workflow(
            workflow_name
        )
        if success and self.backend.workflow_manager.is_system_workflow(workflow_file):
            return (
                False,
                workflow_name,
                f"{workflow_name} is a system workflow, and cannot be deleted",
            )
        confirmation = input(
            f"Are you sure you want to delete workflow {workflow_name}? [y/N] "
        ).strip()
        if confirmation.lower() in ["yes", "y"]:
            success, workflow_name, user_message = self.backend.workflow_manager.delete_workflow(
                workflow_name
            )
            if success:
                self.backend.workflow_manager.load_workflows()
                self.rebuild_completions()
            return success, workflow_name, user_message
        else:
            return False, workflow_name, "Deletion aborted"

    def command_tools(self, arg):
        """
        List available tools

        Tools are pieces of Python code that the LLM can request to be called to perform
        some action.

        They are located in the 'tools' directory in the following locations:

            - The main configuration directory
            - The profile configuration directory

        See {COMMAND_LEADER}config for current locations.

        Arguments:
            filter_string: Optional. If provided, only tools with a name or description containing the filter string will be shown.

        Examples:
            {COMMAND}
            {COMMAND} filterstring
        """
        success, tools, user_message = self.backend.tool_manager.load_tools()
        if not success:
            return success, tools, user_message
        tool_names = []
        for tool_name, _filepath in tools.items():
            tool_config = self.backend.tool_manager.get_tool_config(tool_name)
            content = f"* **{tool_name}**"
            if "description" in tool_config:
                content += f": *{tool_config['description']}*"
            if not arg or arg.lower() in content.lower():
                tool_names.append(content)
        util.print_markdown("## Tools:\n\n%s" % "\n".join(sorted(tool_names)))
