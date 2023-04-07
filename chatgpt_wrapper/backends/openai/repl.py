import getpass
import email_validator

import chatgpt_wrapper.core.constants as constants
import chatgpt_wrapper.core.util as util
from chatgpt_wrapper.core.repl import Repl
from chatgpt_wrapper.backends.openai.database import Database
from chatgpt_wrapper.backends.openai.orm import User
from chatgpt_wrapper.backends.openai.user import UserManager
from chatgpt_wrapper.backends.openai.api import OpenAIAPI

ALLOWED_BASE_SHELL_NOT_LOGGED_IN_COMMANDS = [
    'config',
    'exit',
    'quit',
]

class ApiRepl(Repl):
    """
    A shell interpreter that serves as a front end to the OpenAIAPI class
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
        return {
            util.command_with_leader('model-temperature'): util.float_range_to_completions(constants.OPENAPI_TEMPERATURE_MIN, constants.OPENAPI_TEMPERATURE_MAX),
            util.command_with_leader('model-top-p'): util.float_range_to_completions(constants.OPENAPI_TOP_P_MIN, constants.OPENAPI_TOP_P_MAX),
            util.command_with_leader('model-presence-penalty'): util.float_range_to_completions(constants.OPENAPI_PRESENCE_PENALTY_MIN, constants.OPENAPI_PRESENCE_PENALTY_MAX),
            util.command_with_leader('model-frequency-penalty'): util.float_range_to_completions(constants.OPENAPI_FREQUENCY_PENALTY_MIN, constants.OPENAPI_FREQUENCY_PENALTY_MAX),
            util.command_with_leader('model-system-message'): util.list_to_completion_hash(self.backend.get_system_message_aliases()),
        }

    def configure_backend(self):
        self.backend = OpenAIAPI(self.config)
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

    def select_model(self, allow_empty=False):
        models = list(self.backend.available_models.keys())
        for i, model in enumerate(models):
            print(f"{i + 1}. {model}")
        selected_model = input("Choose a default model: ").strip() or None
        if not selected_model and allow_empty:
            return True, None
        if not selected_model or not selected_model.isdigit() or not (1 <= int(selected_model) <= len(models)):
            return False, "Invalid default model."
        default_model = models[int(selected_model) - 1]
        return True, default_model

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
            default_model: Required, the default AI model to use for this user

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
        # success, default_model = self.select_model()
        # if not success:
        #     return False, None, "Invalid default model."
        # return self.user_management.register(username, email, password, default_model)
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
        prompt_prefix = prompt_prefix.replace("$NEWLINE", "\n")
        prompt_prefix = prompt_prefix.replace("$TEMPERATURE", str(self.backend.model_temperature))
        prompt_prefix = prompt_prefix.replace("$TOP_P", str(self.backend.model_top_p))
        prompt_prefix = prompt_prefix.replace("$PRESENCE_PENALTY", str(self.backend.model_presence_penalty))
        prompt_prefix = prompt_prefix.replace("$FREQUENCY_PENALTY", str(self.backend.model_frequency_penalty))
        prompt_prefix = prompt_prefix.replace("$MAX_SUBMISSION_TOKENS", str(self.backend.model_max_submission_tokens))
        prompt_prefix = prompt_prefix.replace("$CURRENT_CONVERSATION_TOKENS", str(self.backend.conversation_tokens))
        return f"{prompt_prefix} "

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
* Default model: %s
        """ % (user.username, user.email, "set" if user.password else "Not set", self.backend.available_models[user.default_model])
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
            user_list = ["* %s: %s (%s)" % (user.id, user.username, user.default_model) for user in users]
            user_list.insert(0, "# Users")
            util.print_markdown("\n".join(user_list))
        else:
            return success, users, message

    def edit_user(self, user):
        util.print_markdown(f"## Editing user: {user.username}")
        username = input("New username (Press enter to skip): ").strip() or None
        email = input("New email (Press enter to skip): ").strip() or None
        if email:
            success, message = self.validate_email(email)
            if not success:
                return False, email, message
        password = getpass.getpass(prompt='New password (Press enter to skip): ') or None
        success, default_model = self.select_model(True)
        if not success:
            return False, default_model, "Invalid default model."

        kwargs = {
            "username": username,
            "email": email,
            "password": password,
            "default_model": default_model,
        }
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        success, user, user_message = self.user_management.edit_user(user.id, **kwargs)
        if success:
            self.rebuild_completions()
            if self.logged_in_user.id == user.id:
                self.backend.set_active_model(user.default_model)
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

    def adjust_model_setting(self, value_type, setting, value, min=None, max=None):
        if not self._is_logged_in():
            return False, None, "Not logged in."
        if value:
            method = getattr(util, f"validate_{value_type}")
            value = method(value, min, max)
            if value is False:
                return False, value, f"Invalid {setting}, must be float between {min} and {max}."
            else:
                method = getattr(self.backend, f"set_model_{setting}")
                method(value)
                return True, value, f"{setting} set to {value}"
        else:
            value = getattr(self.backend, f"model_{setting}")
            util.print_markdown(f"* Current {setting}: {value}")

    def do_model_temperature(self, temperature=None):
        """
        Adjust the temperature of the current model

        What sampling temperature to use.

        Higher values like 0.8 will make the output more random, while lower values
        like 0.2 will make it more focused and deterministic.

        Recommend altering this or top_p but not both.

        Arguments:
            temperature: Float between {OPENAPI_TEMPERATURE_MIN} and {OPENAPI_TEMPERATURE_MAX}, default: {OPENAPI_DEFAULT_TEMPERATURE}

        Examples:
            {COMMAND}
            {COMMAND} {OPENAPI_TEMPERATURE_MAX}
        """
        return self.adjust_model_setting("float", "temperature", temperature, constants.OPENAPI_TEMPERATURE_MIN, constants.OPENAPI_TEMPERATURE_MAX)

    def do_model_top_p(self, top_p=None):
        """
        Adjust the top_p of the current model

        An alternative to sampling with temperature.

        Nucleus sampling, where the model considers the results of the tokens with
        top_p probability mass. So 0.1 means only the tokens comprising the top 10%
        probability mass are considered.

        Recommend altering this or temperature but not both.

        Arguments:
            top_p: Float between {OPENAPI_TOP_P_MIN} and {OPENAPI_TOP_P_MAX}, default: {OPENAPI_DEFAULT_TOP_P}

        Examples:
            {COMMAND}
            {COMMAND} {OPENAPI_TOP_P_MAX}
        """
        return self.adjust_model_setting("float", "top_p", top_p, constants.OPENAPI_TOP_P_MIN, constants.OPENAPI_TOP_P_MAX)

    def do_model_presence_penalty(self, presence_penalty=None):
        """
        Adjust the presence penalty of the current model

        The presence penalty penalizes new tokens based on whether they appear in the
        text so far. Positive values increase the model's likelihood to talk about new
        topics.

        Arguments:
            presence_penalty: Float between {OPENAPI_PRESENCE_PENALTY_MIN} and {OPENAPI_PRESENCE_PENALTY_MAX}, default: {OPENAPI_DEFAULT_PRESENCE_PENALTY}

        Examples:
            {COMMAND}
            {COMMAND} {OPENAPI_PRESENCE_PENALTY_MAX}
        """
        return self.adjust_model_setting("float", "presence_penalty", presence_penalty, constants.OPENAPI_PRESENCE_PENALTY_MIN, constants.OPENAPI_PRESENCE_PENALTY_MAX)

    def do_model_frequency_penalty(self, frequency_penalty=None):
        """
        Adjust the frequency_penalty of the current model

        The frequency penalty penalizes new tokens based on their frequency in the
        text so far. Positive values can help prevent the model from repeating itself.

        Arguments:
            frequency_penalty: Float between {OPENAPI_FREQUENCY_PENALTY_MIN} and {OPENAPI_FREQUENCY_PENALTY_MAX}, default: {OPENAPI_DEFAULT_FREQUENCY_PENALTY}

        Examples:
            {COMMAND}
            {COMMAND} {OPENAPI_FREQUENCY_PENALTY_MAX}
        """
        return self.adjust_model_setting("float", "frequency_penalty", frequency_penalty, constants.OPENAPI_FREQUENCY_PENALTY_MIN, constants.OPENAPI_FREQUENCY_PENALTY_MAX)

    def do_model_max_submission_tokens(self, max_submission_tokens=None):
        """
        The maximum number of tokens that can be submitted before older messages
        start getting cut off.

        Current max tokens for both submission and reply are {OPENAPI_MAX_TOKENS}, so the current
        default will still allow for a short reply from the model.

        Arguments:
            max_submission_tokens: Integer between {OPENAPI_MIN_SUBMISSION_TOKENS} and {OPENAPI_MAX_TOKENS}, default: {OPENAPI_DEFAULT_MAX_SUBMISSION_TOKENS}

        Examples:
            {COMMAND}
            {COMMAND} {OPENAPI_DEFAULT_MAX_SUBMISSION_TOKENS}
        """
        return self.adjust_model_setting("int", "max_submission_tokens", max_submission_tokens, constants.OPENAPI_MIN_SUBMISSION_TOKENS, constants.OPENAPI_MAX_TOKENS)

    def do_model_system_message(self, system_message=None):
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
        aliases = self.backend.get_system_message_aliases()
        if system_message:
            if system_message in aliases:
                system_message = aliases[system_message]
            return self.adjust_model_setting("str", "system_message", system_message, constants.OPENAPI_MIN_SUBMISSION_TOKENS, self.backend.model_max_submission_tokens)
        else:
            output = "## System message:\n\n%s\n\n## Available aliases:\n\n%s" % (self.backend.model_system_message, "\n".join([f"* {a}" for a in aliases.keys()]))
            util.print_markdown(output)
