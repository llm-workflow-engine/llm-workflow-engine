#!/usr/bin/env python

import names
import argparse

from rich.console import Console
from rich.markdown import Markdown

from sqlalchemy.exc import OperationalError

from chatgpt_wrapper.openai.orm import Base, Orm
from chatgpt_wrapper.logger import Logger
from chatgpt_wrapper.config import Config
import chatgpt_wrapper.debug as debug
if False:
    debug.console(None)

DEFAULT_NUM_USERS = 5
DEFAULT_NUM_CONVERSATIONS = 5
DEFAULT_NUM_MESSAGES = 10

console = Console()

class Database:

    def __init__(self, config):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.orm = Orm(self.config)

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
        if not self.schema_exists():
            console.print(f"Creating database schema for: {self.orm.database}", style="bold green")
            Base.metadata.create_all(bind=self.orm.engine)
            console.print("Database schema installed", style="bold green")

    def remove_schema(self):
        if self.schema_exists():
            console.print(f"Removing old database schema for: {self.orm.database}", style="bold red")
            Base.metadata.drop_all(bind=self.orm.engine)
            console.print("Removed old database schema", style="bold green")

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
        console.print("Creating users...", style="bold green")
        # Create Users
        for i in range(self.num_users):
            username = names.get_full_name().lower().replace(" ", ".")
            password = 'password'
            email = f'{username}@example.com'
            user = self.orm.add_user(username, password, email)
            console.print(f"Created user: {user.username}", style="blue")
            # Create Conversations for each User
            console.print(f"Creating {self.num_conversations} conversations and {self.num_messages} messages for: {user.username}...", style="white")
            for j in range(self.num_conversations):
                title = f'Conversation {j+1} for User {i+1}'
                conversation = self.orm.add_conversation(user, title)
                # Create Messages for each Conversation
                for k in range(self.num_messages):
                    role = 'user' if k % 2 == 0 else 'assistant'
                    message = f'This is message {k+1} in conversation {j+1} for user {i+1}'
                    message = self.orm.add_message(conversation, role, message)

    def print_data(self):
        output = ['# Users']
        users = self.orm.get_users()
        for user in users:
            conversations = self.orm.get_conversations(user)
            output.append(f'## User {user.id}: {user.username}, conversations: {len(conversations)}')
            for conversation in conversations:
                messages = self.orm.get_messages(conversation)
                output.append(f'### {conversation.title}, messages: {len(messages)}')
                for message in messages:
                    output.append(f'* {message.role}: {message.message}')
        console.print(Markdown("\n".join(output)))

    def run(self):
        if self.create:
            if self.schema_exists():
                if self.force:
                    console.print("Force specified", style="bold red")
                    self.remove_schema()
                    self.create_schema()
            else:
                self.create_schema()
        if self.test_data:
            if self.schema_exists():
                self.create_test_data()
            else:
                console.print("Cannot create test data, database not created, use --create to create it", style="bold red")
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
        config.set('database', args.database)
    db = DatabaseDevel(config, args)
    db.run()

if __name__ == '__main__':
    main()
