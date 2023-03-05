import getpass
import email_validator
from typing import Tuple

import chatgpt_wrapper.openai.api as Api
from chatgpt_wrapper.openai.orm import User
from chatgpt_wrapper.openai.user import UserManagement
from chatgpt_wrapper.openai.api import OpenAIAPI
from chatgpt_wrapper.gpt_shell import GPTShell

class ApiShell(GPTShell):
    """
    A shell interpreter that serves as a front end to the ChatGPT class
    """

    def __init__(self, config=None):
        super().__init__(config)
        self.database = self.config.get('database')
        self.user_management = UserManagement(self.database)
        self.logged_in_user_id = None

    def configure_commands(self):
        super().configure_commands()
        self.commands.extend([method[3:] for method in dir(__class__) if callable(getattr(__class__, method)) and method.startswith("do_")])

    async def configure_backend(self):
        self.backend = OpenAIAPI(self.config)

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
        user = self.user_management.session.get(User, user_id)
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
        return model in Api.RENDER_MODELS.keys()

    def select_model(self, allow_empty: bool = False) -> Tuple[bool, str]:
        for i, model in enumerate(Api.RENDER_MODELS.keys()):
            print(f"{i + 1}. {model}")
        selected_model = input("Choose a default model: ").strip() or None
        if not selected_model and allow_empty:
            return True, None
        if not selected_model or not selected_model.isdigit() or not (1 <= int(selected_model) <= len(Api.RENDER_MODELS)):
            return False, "Invalid default model."
        default_model = list(Api.RENDER_MODELS.values())[int(selected_model) - 1]
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
            username = input("Enter username: ").strip() or None
            if not username:
                return False, "Username cannot be empty."
        email = input("Enter email: ").strip() or None
        if email:
            success, message = self.validate_email(email)
            if not success:
                return False, message
        password = input("Enter password: ").strip() or None
        success, default_model = self.select_model()
        if not success:
            return False, "Invalid default model."
        return self.user_management.register(username, email, password, default_model)

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
        if not user:
            return False, f"User {identifier} not found."
        if not user.password:
            self.logged_in_user_id = user.id
            return True, "Login successful."
        else:
            password = getpass.getpass(prompt='Enter password: ')
            result, message = self.user_management.login(identifier, password)
            if result:
                self.logged_in_user_id = user.id
            return result, message

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
            return False, "Not logged in."
        self.logged_in_user_id = None
        return True, "Logout successful."

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
            return False, "Not logged in."
        if username:
            success, user = self.user_management.get_by_username(username)
            if success:
                return self.display_user(user)
        else:
            user = self.get_logged_in_user()
            if user:
                return self.display_user(user)
        return False, "User not found."

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
            return False, "Not logged in."
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
            return False, "Not logged in."
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
