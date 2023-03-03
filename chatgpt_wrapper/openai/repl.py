import sys
import re
import logging
import getpass
import email_validator
from typing import Tuple

from rich.console import Console
from rich.markdown import Markdown

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter

import chatgpt_wrapper.debug as debug
import chatgpt_wrapper.openai.api as Api
from chatgpt_wrapper.openai.orm import User
from chatgpt_wrapper.openai.user import UserManagement

DEFAULT_DATABASE = "sqlite:////tmp/chatgpt-test.db"
COMMAND_LEADER = '/'

console = Console()

command_pattern_matcher = re.compile(r"([a-zA-Z0-9_" + COMMAND_LEADER + r"]+|[^a-zA-Z0-9_\s]+)")

class Repl:
    def __init__(self, user_management: UserManagement):
        self.user_management = user_management
        self.logged_in_user_id = None

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

    def do_register(self, username: str = None) -> Tuple[bool, str]:
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

    def do_login(self, identifier: str = None) -> Tuple[bool, str]:
        if not identifier:
            identifier = input("Enter username or email: ")
        user = self.user_management.session.query(User).filter(
            (User.username == identifier.lower()) | (User.email == identifier.lower())
        ).first()
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

    def do_logout(self, _) -> Tuple[bool, str]:
        if not self._is_logged_in():
            return False, "Not logged in."
        self.logged_in_user_id = None
        return True, "Logout successful."

    def do_edit(self, username: str = None) -> Tuple[bool, str]:
        if not self._is_logged_in():
            return False, "Not logged in."
        user = self.get_logged_in_user()
        if not user:
            return False, "User not found."
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

    def do_delete(self, username: str = None) -> Tuple[bool, str]:
        if not self._is_logged_in():
            return False, "Not logged in."
        if not username:
            username = input("Enter username: ")
        user = self.user_management.session.query(User).filter(User.username == username.lower()).first()
        if user:
            if user.id == self.logged_in_user_id:
                return False, "Cannot delete currently logged in user."
            else:
                return self.user_management.delete(user.id)
        else:
            return False, "User does not exist."

    def run(self) -> None:
        commands = [
            "/register",
            "/login",
            "/logout",
            "/edit",
            "/delete",
            "/exit"
        ]
        command_completer = WordCompleter(commands, ignore_case=True, pattern=command_pattern_matcher)
        prompt_session = PromptSession(completer=command_completer)
        while True:
            text = prompt_session.prompt("> ")
            text = text.strip()
            if not text:
                continue
            leader = text[0]
            if leader == COMMAND_LEADER:
                text = text[1:]
                parts = [arg.strip() for arg in text.split(maxsplit=1)]
                command = parts[0]
                argument = parts[1] if len(parts) > 1 else ''
                if command == "exit" or command == "quit":
                    break
                method = getattr(__class__, f"do_{command}", None)
                if method:
                    try:
                        success, response = method(self, argument)
                    except Exception as e:
                        print(repr(e))
                    else:
                        if success:
                            console.print(Markdown(response))
                        else:
                            console.print(f"ERROR: {response}", style="bold red")
                else:
                    console.print(f"Unknown command: {command}", style="bold red")
            else:
                console.print("Invalid entry.", style="bold red")

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    database = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DATABASE
    user_management = UserManagement(database)
    repl = Repl(user_management)
    repl.run()
