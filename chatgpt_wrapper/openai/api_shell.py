import getpass
import email_validator
from typing import Tuple

import chatgpt_wrapper.constants as constants
from chatgpt_wrapper.openai.database import Database
from chatgpt_wrapper.openai.orm import User
from chatgpt_wrapper.openai.user import UserManagement
from chatgpt_wrapper.openai.api import OpenAIAPI
from chatgpt_wrapper.gpt_shell import GPTShell
import chatgpt_wrapper.debug as debug
if False:
    debug.console(None)

ALLOWED_BASE_SHELL_NOT_LOGGED_IN_COMMANDS = [
    'config',
    'exit',
    'quit',
]

class ApiShell(GPTShell):
    """
    A shell interpreter that serves as a front end to the ChatGPT class
    """

    def __init__(self, config=None):
        super().__init__(config)
        self.logged_in_user_id = None

    def not_logged_in_disallowed_commands(self):
        base_shell_commands = self._introspect_commands(GPTShell)
        disallowed_commands = [c for c in base_shell_commands if c not in ALLOWED_BASE_SHELL_NOT_LOGGED_IN_COMMANDS]
        return disallowed_commands

    def exec_prompt_pre(self, command, arg):
        if not self.logged_in_user_id and command in self.not_logged_in_disallowed_commands():
            return False, None, "Must be logged in to execute %s%s" % (constants.COMMAND_LEADER, command)

    def configure_commands(self):
        self.commands = self._introspect_commands(__class__)

    async def configure_backend(self):
        self.backend = OpenAIAPI(self.config)
        database = Database(self.config)
        database.create_schema()
        self.user_management = UserManagement(self.config)
        self.session = self.user_management.orm.session
        await self.check_login()

    # TODO: Implement this
    def _conversation_from_messages(self, messages):
        message_parts = []
        for message in messages:
            if 'content' in message:
                message_parts.append("**%s**:" % message['author']['role'].capitalize())
                message_parts.extend(message['content']['parts'])
        content = "\n\n".join(message_parts)
        return content

    def get_logged_in_user(self) -> User:
        if self.logged_in_user_id:
            return self.get_user(self.logged_in_user_id)

    def get_user(self, user_id) -> User:
        user = self.session.get(User, user_id)
        return user

    def _is_logged_in(self) -> bool:
        return self.logged_in_user_id is not None

    def validate_email(self, email: str) -> Tuple[bool, str]:
        try:
            valid = email_validator.validate_email(email)
            return True, valid.email
        except email_validator.EmailNotValidError as e:
            return False, f"Invalid email: {e}"

    def validate_model(model: str) -> bool:
        return model in constants.API_RENDER_MODELS.keys()

    def select_model(self, allow_empty: bool = False) -> Tuple[bool, str]:
        models = list(constants.API_RENDER_MODELS.keys())
        for i, model in enumerate(models):
            print(f"{i + 1}. {model}")
        selected_model = input("Choose a default model: ").strip() or None
        if not selected_model and allow_empty:
            return True, None
        if not selected_model or not selected_model.isdigit() or not (1 <= int(selected_model) <= len(models)):
            return False, "Invalid default model."
        default_model = models[int(selected_model) - 1]
        return True, default_model

    async def do_user_register(self, username: str = None) -> Tuple[bool, str]:
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
            {leader}user_register
            {leader}user_register myusername
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
        success, default_model = self.select_model()
        if not success:
            return False, None, "Invalid default model."
        return self.user_management.register(username, email, password, default_model)

    async def check_login(self):
        user_count = self.session.query(User).count()
        if user_count == 0:
            self.console.print("No users in database. Creating one...", style="bold red")
            self.welcome_message()
            await self.create_first_user()
        # Special case check: if there's only one user in the database, and
        # they have no password, log them in.
        elif user_count == 1:
            user = self.session.query(User).first()
            if not user.password:
                return self.login(user)

    def welcome_message(self):
        self._print_markdown(
"""
# Welcome to the ChatGPT API shell!

This shell interacts directly with the ChatGPT API, and stores conversations and messages in the configured database.

Before you can start using the shell, you must create a new user.
"""
        )

    async def create_first_user(self):
        success, user, message = await self.do_user_register()
        self._print_status_message(success, message)
        if success:
            success, _user, message = self.login(user)
            self._print_status_message(success, message)
        else:
            await self.create_first_user()

    def set_user_prompt(self, user=None):
        if self.logged_in_user_id and user:
            prefix = f"{user.username} "
        else:
            prefix = ''
        self._set_prompt_prefix(prefix)
        self._set_prompt()

    def login(self, user):
        if user.password:
            password = getpass.getpass(prompt='Enter password: ')
            success, user, message = self.user_management.login(user.username, password)
            if success:
                self.logged_in_user_id = user.id
        else:
            self.logged_in_user_id = user.id
            self.backend.set_current_user(user)
            success, user, message = True, user, "Login successful."
        self.set_user_prompt(user)
        return success, user, message

    async def do_user_login(self, identifier: str = None) -> Tuple[bool, str]:
        """
        Login in as a user

        If the 'identifier' argument is not provided, you will be prompted for either a username or email.
        You will be prompted for a password if one is set for the user.

        Arguments:
            identifier: The username or email

        Examples:
            {leader}user_login
            {leader}user_login myusername
            {leader}user_login email@example.com
        """
        if not identifier:
            identifier = input("Enter username or email: ")
        user = self.user_management.find_user_by_username_or_email(identifier)
        if user:
            return self.login(user)
        return False, None, f"User {identifier} not found."

    async def do_login(self, identifier: str = None) -> Tuple[bool, str]:
        """
        Alias of '{leader}user_login'

        Login in as a user.

        Arguments:
            identifier: The username or email

        Examples:
            {leader}login
            {leader}login myusername
            {leader}login email@example.com
        """
        return await self.do_user_login(identifier)

    async def do_user_logout(self, _) -> Tuple[bool, str]:
        """
        Logout the current user.

        Examples:
            {leader}user_logout
        """
        if not self._is_logged_in():
            return False, None, "Not logged in."
        self.logged_in_user_id = None
        self.backend.set_current_user()
        self.set_user_prompt()
        return True, None, "Logout successful."

    async def do_logout(self, _) -> Tuple[bool, str]:
        """
        Alias of '{leader}user_logout'

        Logout the current user.

        Examples:
            {leader}logout
        """
        return await self.do_user_logout(None)

    def display_user(self, user):
        output = f"""
## Username: %s

* Email: %s
* Password: %s
* Default model: %s
        """ % (user.username, user.email, "set" if user.password else "not set", user.default_model)
        self._print_markdown(output)

    async def do_user(self, username: str = None) -> Tuple[bool, str]:
        """
        Show user information

        Arguments:
            username: The username of the user to show, if not provided, the logged in user will be used.

        Examples:
            {leader}user
            {leader}user ausername
        """
        if not self._is_logged_in():
            return False, None, "Not logged in."
        if username:
            success, user = self.user_management.get_by_username(username)
            if success:
                return self.display_user(user)
        else:
            user = self.get_logged_in_user()
            if user:
                return self.display_user(user)
        return False, "User not found."

    async def do_users(self, _) -> Tuple[bool, str]:
        """
        Show information for all users

        Examples:
            {leader}users
        """
        _success, users, _message = self.user_management.list()
        user_list = ["* %s (%s)" % (user.username, user.default_model) for user in users]
        user_list.insert(0, "# Users")
        self._print_markdown("\n".join(user_list))

    def edit_user(self, user):
        self._print_markdown(f"## Editing user: {user.username}")
        username = input("New username (Press enter to skip): ").strip() or None
        email = input("New email (Press enter to skip): ").strip() or None
        if email:
            success, message = self.validate_email(email)
            if not success:
                return False, message
        password = getpass.getpass(prompt='New password (Press enter to skip): ') or None
        success, default_model = self.select_model(True)
        if not success:
            return False, "Invalid default model."

        kwargs = {
            "username": username,
            "email": email,
            "password": password,
            "default_model": default_model,
        }
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        return self.user_management.edit(user.id, **kwargs)

    async def do_user_edit(self, username: str = None) -> Tuple[bool, str]:
        """
        Edit the current user's information

        You will be prompted to enter new values for the username, email, password, and default model.
        You can skip any prompt by pressing enter.

        Examples:
            {leader}user_edit
        """
        if not self._is_logged_in():
            return False, None, "Not logged in."
        if username:
            user = self.user_management.find_user_by_username(username)
            if user:
                return self.edit_user(user)
        else:
            user = self.get_logged_in_user()
            if user:
                return self.edit_user(user)
        return False, "User not found."

    async def do_user_delete(self, username: str = None) -> Tuple[bool, str]:
        """
        Delete a user

        If the 'username' argument is not provided, you will be prompted for it.
        The currently logged in user cannot be deleted.

        Arguments:
            username: The username of the user to be deleted

        Examples:
            {leader}user_delete
            {leader}user_delete myusername
        """
        if not self._is_logged_in():
            return False, None, "Not logged in."
        if not username:
            username = input("Enter username: ")
        user = self.user_management.find_user_by_username(username)
        if user:
            if user.id == self.logged_in_user_id:
                return False, "Cannot delete currently logged in user."
            else:
                return self.user_management.delete(user.id)
        else:
            return False, "User does not exist."
