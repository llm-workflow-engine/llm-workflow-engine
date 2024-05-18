#!/usr/bin/env python

import names
import argparse

from sqlalchemy.exc import OperationalError

from lwe.core import constants
from lwe.backends.api.orm import Base, Orm
from lwe.backends.api.user import UserManager
from lwe.backends.api.conversation import ConversationManager
from lwe.backends.api.message import MessageManager
from lwe.backends.api.schema.updater import SchemaUpdater
from lwe.core.logger import Logger
from lwe.core.config import Config
import lwe.core.util as util

DEFAULT_NUM_USERS = 5
DEFAULT_NUM_CONVERSATIONS = 5
DEFAULT_NUM_MESSAGES = 10


class Database:
    def __init__(self, config, orm=None):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.orm = orm or Orm(self.config)
        self.user_manager = UserManager(self.config, self.orm)
        self.conversation = ConversationManager(self.config, self.orm)
        self.message = MessageManager(self.config, self.orm)

    def schema_exists(self):
        # Necessary to create a new engine/metadata here, as the tables are cached,
        # and we need to know the current state.
        _, metadata = self.orm.create_engine_and_metadata()
        try:
            if len(metadata.tables.keys()) > 0:
                self.log.debug("The database schema exists.")
                return True
        except OperationalError:
            self.log.warning("The database schema does not exist.")
            return False

    def create_schema(self):
        updater = SchemaUpdater(self.config, self.orm)
        if self.schema_exists():
            updater.update_schema()
        else:
            util.print_status_message(True, f"Creating database schema for: {self.orm.database}")
            Base.metadata.create_all(bind=self.orm.engine)
            updater.init_alembic()
            util.print_status_message(True, "Database schema installed")

    def remove_schema(self):
        if self.schema_exists():
            util.print_status_message(
                False, f"Removing old database schema for: {self.orm.database}"
            )
            Base.metadata.drop_all(bind=self.orm.engine)
            util.print_status_message(True, "Removed old database schema")


class DatabaseDevel(Database):
    def __init__(self, config, args):
        super().__init__(config)
        self.num_users = args.users or DEFAULT_NUM_USERS
        self.num_conversations = args.conversations or DEFAULT_NUM_CONVERSATIONS
        self.num_messages = args.messages or DEFAULT_NUM_MESSAGES
        self.create = args.create
        self.force = args.force
        self.test_data = args.test_data
        self.print = args.print

    def create_test_data(self):
        util.print_status_message(True, "Creating users...")
        # Create Users
        for i in range(self.num_users):
            username = names.get_full_name().lower().replace(" ", ".")
            password = None
            email = f"{username}@example.com"
            user = self.user_manager.add_user(username, password, email)
            util.print_status_message(True, f"Created user: {user.username}", style="bold blue")
            # Create Conversations for each User
            util.print_status_message(
                True,
                f"Creating {self.num_conversations} conversations and {self.num_messages} messages for: {user.username}...",
                style="white",
            )
            for j in range(self.num_conversations):
                title = f"Conversation {j + 1} for User {i + 1}"
                conversation = self.conversation.add_conversation(user, title)
                # Create Messages for each Conversation
                for k in range(self.num_messages):
                    role = "user" if k % 2 == 0 else "assistant"
                    message = f"This is message {k + 1} in conversation {j + 1} for user {i + 1}"
                    message = self.message.add_message(
                        conversation,
                        role,
                        message,
                        "content",
                        "",
                        "chat_openai",
                        constants.API_BACKEND_DEFAULT_MODEL,
                        "",
                    )

    def print_data(self):
        output = ["# Users"]
        users = self.user_manager.get_users()
        for user in users:
            conversations = self.conversation.get_conversations(user)
            output.append(
                f"## User {user.id}: {user.username}, conversations: {len(conversations)}"
            )
            for conversation in conversations:
                messages = self.message.get_messages(conversation)
                output.append(f"### {conversation.title}, messages: {len(messages)}")
                for message in messages:
                    output.append(f"* {message.role}: {message.message}")
        util.print_markdown("\n".join(output))

    def run(self):
        if self.create:
            if self.schema_exists():
                if self.force:
                    util.print_status_message(False, "Force specified")
                    self.remove_schema()
                    self.create_schema()
            else:
                self.create_schema()
        if self.test_data:
            if self.schema_exists():
                self.create_test_data()
            else:
                util.print_status_message(
                    False,
                    "Cannot create test data, database not created, use --create to create it",
                )
        if self.print:
            self.print_data()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--create",
        action="store_true",
        help="create the database and tables",
    )
    parser.add_argument(
        "-t",
        "--test-data",
        action="store_true",
        help="populate the database tables with test data",
    )
    parser.add_argument(
        "-p",
        "--print",
        action="store_true",
        help="print out the created data",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="force remove and re-create the database",
    )
    parser.add_argument(
        "-d",
        "--database",
        action="store",
        help="database filepath",
    )
    parser.add_argument(
        "-u",
        "--users",
        action="store",
        help="number of users to create, default: %s" % DEFAULT_NUM_USERS,
    )
    parser.add_argument(
        "-n",
        "--conversations",
        action="store",
        help="number of conversations per user to create, default: %s" % DEFAULT_NUM_CONVERSATIONS,
    )
    parser.add_argument(
        "-m",
        "--messages",
        action="store",
        help="number of messages per conversation to create, default: %s" % DEFAULT_NUM_MESSAGES,
    )
    args = parser.parse_args()

    if not (args.create or args.test_data or args.print):
        parser.error("At least one of --create, --test-data, --print must be set")

    config = Config()
    config.load_from_file()
    if args.database:
        config.set("database", args.database)
    db = DatabaseDevel(config, args)
    db.run()


if __name__ == "__main__":
    main()
