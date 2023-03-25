import hashlib
import datetime

from sqlalchemy.exc import SQLAlchemyError

from chatgpt_wrapper.backends.openai.orm import Manager, User

class UserManager(Manager):
    def _hash_password(self, password):
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        return hashed_password

    def user_found_message(self, user):
        found = "found" if user else "not found"
        return f"User {found}."

    def get_by_user_id(self, user_id):
        try:
            user = self.orm.get_user(user_id)
        except SQLAlchemyError as e:
            return self._handle_error(f"Failed to get user: {str(e)}")
        return True, user, self.user_found_message(user)

    def get_by_username(self, username):
        username = username.lower()
        try:
            user = self.orm.session.query(User).filter(
                (User.username == username)
            ).first()
        except SQLAlchemyError as e:
            return self._handle_error(f"Failed to get user: {str(e)}")
        return True, user, self.user_found_message(user)

    def get_by_username_or_email(self, identifier):
        identifier = identifier.lower()
        try:
            user = self.orm.session.query(User).filter(
                (User.username == identifier) | (User.email == identifier)
            ).first()
        except SQLAlchemyError as e:
            return self._handle_error(f"Failed to get user: {str(e)}")
        return True, user, self.user_found_message(user)

    def register(self, username, email, password, default_model='default', preferences={}):
        username = username.lower()
        if email:
            email = email.lower()
        if password:
            password = self._hash_password(password)
        # Check if the username or email is equal to the email of an existing user.
        if email:
            try:
                existing_user = self.orm.session.query(User).filter(
                    (User.username == username) | (User.username == email) | (User.email == email) | (User.email == username)
                ).first()
            except SQLAlchemyError as e:
                return self._handle_error(f"Failed to retrieve existing users: {str(e)}")
        else:
            success, existing_user, message = self.get_by_username_or_email(username)
            if not success:
                return success, existing_user, message
        if existing_user:
            return False, None, "Username or email is already in use."
        try:
            user = self.orm.add_user(username, password, email, default_model, preferences)
        except SQLAlchemyError as e:
            return self._handle_error(f"Failed to add user: {str(e)}")
        return True, user, "User successfully registered."

    def login(self, identifier, password):
        success, user, message = self.get_by_username_or_email(identifier)
        if not success:
            return success, user, message
        if not user:
            return False, None, "Username or email not found."
        # Hash the password and compare it to the hashed password in the database
        if self._hash_password(password) != user.password:
            return False, user, "Incorrect password."
        # Update the last login time
        user.last_login_time = datetime.datetime.utcnow()
        try:
            self.orm.session.commit()
            self.orm.session.refresh(user)
        except SQLAlchemyError as e:
            return self._handle_error(f"Failed to log in user: {str(e)}")
        return True, user, "Login successful."

    def logout(self, user_id):
        # Logout functionality is usually implemented on the frontend, so this method can be left blank
        pass

    def get_users(self, limit=None, offset=None):
        try:
            users = self.orm.get_users(limit, offset)
        except SQLAlchemyError as e:
            return self._handle_error(f"Failed to get users: {str(e)}")
        return True, users, "Users retrieved."

    def edit_user(self, user_id, username=None, email=None, password=None, default_model=None):
        success, user, message = self.get_by_user_id(user_id)
        if not success:
            return success, user, message
        if not user:
            return False, None, "User not found."
        kwargs = {}
        # Check if the new username or email is equal any existing user username or email.
        if username:
            success, existing_user, message = self.get_by_username_or_email(username)
            if not success:
                return success, existing_user, message
            if existing_user and existing_user.id != user.id:
                return False, user, "Username cannot be the same as an existing user's email."
            kwargs['username'] = username
        if email:
            success, existing_user, message = self.get_by_username_or_email(email)
            if not success:
                return success, existing_user, message
            if existing_user and existing_user.id != user.id:
                return False, user, "Email cannot be the same as an existing user's username."
            kwargs['email'] = email
        if password:
            kwargs['password'] = self._hash_password(password)
        if default_model:
            kwargs['default_model'] = default_model
        try:
            user = self.orm.edit_user(user, **kwargs)
        except SQLAlchemyError as e:
            return self._handle_error(f"Failed to edit user: {str(e)}")
        return True, user, "User successfully edited."

    def delete_user(self, user_id):
        success, user, message = self.get_by_user_id(user_id)
        if not success:
            return success, user, message
        if not user:
            return False, None, "User not found."
        try:
            user = self.orm.delete_user(user)
        except SQLAlchemyError as e:
            return self._handle_error(f"Failed to delete user: {str(e)}")
        return True, user, "User successfully deleted."
