import hashlib
import datetime

from chatgpt_wrapper.config import Config
from chatgpt_wrapper.logger import Logger
from chatgpt_wrapper.openai.orm import Orm, User
import chatgpt_wrapper.debug as debug
if False:
    debug.console(None)

class UserManagement:
    def __init__(self, config=None):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.orm = Orm(self.config)

    def find_user_by_id(self, user_id):
        user = self.orm.get_user(user_id)
        return user

    def find_user_by_username(self, username):
        username = username.lower()
        user = self.orm.session.query(User).filter(
            (User.username == username)
        ).first()
        return user

    def find_user_by_username_or_email(self, username_or_email):
        identifier = username_or_email.lower()
        user = self.orm.session.query(User).filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()
        return user

    def hash_password(self, password):
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        return hashed_password

    def register(self, username, email, password, default_model='default', preferences={}):
        username = username.lower()
        if email:
            email = email.lower()
        if password:
            password = self.hash_password(password)
        # Check if the username or email is equal to the email of an existing user.
        if email:
            existing_user = self.orm.session.query(User).filter(
                (User.username == username) | (User.username == email) | (User.email == email) | (User.email == username)
            ).first()
        else:
            existing_user = self.find_user_by_username_or_email(username)
        if existing_user:
            return False, None, "Username or email is already in use."
        user = self.orm.add_user(username, password, email, default_model, preferences)
        return True, user, "User successfully registered."

    def login(self, identifier, password):
        # Get the user with the specified identifier (username or email)
        user = self.find_user_by_username_or_email(identifier)
        if not user:
            return False, None, "Username or email not found."
        # Hash the password and compare it to the hashed password in the database
        if self.hash_password(password) != user.password:
            return False, user, "Incorrect password."
        # Update the last login time
        user.last_login_time = datetime.datetime.utcnow()
        self.orm.session.commit()
        self.orm.session.refresh(user)
        self.orm.session.close()
        return True, user, "Login successful."

    def logout(self, user_id):
        # Logout functionality is usually implemented on the frontend, so this method can be left blank
        pass

    def get_by_username(self, username):
        # Get the user with the specified username
        user = self.find_user_by_username(username)
        if not user:
            return False, None, "User not found."
        return True, user, "User found."

    def list(self, limit=None, offset=None):
        users = self.orm.get_users(limit, offset)
        return True, users, "Users retrieved."

    def edit(self, user_id, username=None, email=None, password=None, default_model=None):
        user = self.find_user_by_id(user_id)
        if not user:
            return False, None, "User not found."
        kwargs = {}
        # Check if the new username or email is equal to the email of an existing user
        if username:
            existing_user = self.find_user_by_username_or_email(username)
            if existing_user and existing_user.id != user.id:
                return False, user, "Username cannot be the same as an existing user's email."
            kwargs[username] = username
        if email:
            existing_user = self.find_user_by_username_or_email(email)
            if existing_user and existing_user.id != user.id:
                return False, user, "Email cannot be the same as an existing user's username."
            kwargs[email] = email

        if password:
            # Hash the password before saving
            kwargs[password] = self.hash_password(password)

        if default_model:
            kwargs[default_model] = default_model
        self.org.edit_user(user, **kwargs)
        return True, user, "User successfully edited."

    def delete(self, user_id):
        # Get the user with the specified user_id
        user = self.find_user_by_id(user_id)
        if not user:
            return False, None, "User not found."

        self.orm.delete_user(user)
        return True, user, "User successfully deleted."
