#!/usr/bin/env python

import os
import time
import logging
import names
import argparse

from rich.console import Console
from rich.markdown import Markdown

from chatgpt_wrapper.openai.orm import Base, Orm, User, Conversation, Message
import chatgpt_wrapper.debug as debug

DEFAULT_DATABASE = "/tmp/chatgpt-test.db"
DEFAULT_NUM_USERS = 5
DEFAULT_NUM_CONVERSATIONS = 5
DEFAULT_NUM_MESSAGES = 10

console = Console()

def create_db(database=DEFAULT_DATABASE):
    console.print(f"Creating database: {database}", style="bold green")
    orm = Orm('sqlite:///%s' % database, logging.WARNING)
    Base.metadata.create_all(orm.engine)
    console.print("Database created", style="bold green")

def create_test_data(database=DEFAULT_DATABASE, num_users=DEFAULT_NUM_USERS, num_conversations=DEFAULT_NUM_CONVERSATIONS, num_messages=DEFAULT_NUM_MESSAGES):
    orm = Orm('sqlite:///%s' % database, logging.WARNING)
    console.print("Creating users...", style="bold green")
    # Create Users
    for i in range(num_users):
        username = names.get_full_name().lower().replace(" ", ".")
        password = 'password'
        email = f'{username}@example.com'
        user = orm.add_user(username, password, email)
        console.print(f"Created user: {user.username}", style="blue")
        # Create Conversations for each User
        console.print(f"Creating {num_conversations} conversations and {num_conversations * num_messages} messages for: {user.username}...", style="white")
        for j in range(num_conversations):
            title = f'Conversation {j+1} for User {i+1}'
            conversation = orm.add_conversation(user, title)
            # Create Messages for each Conversation
            for k in range(num_messages):
                role = 'user' if k % 2 == 0 else 'assistant'
                message = f'This is message {k+1} in conversation {j+1} for user {i+1}'
                message = orm.add_message(conversation, role, message)

def remove_db(database=DEFAULT_DATABASE):
    console.print(f"Removing old database: {database}", style="bold red")
    os.remove(database)

def print_data(database=DEFAULT_DATABASE):
    orm = Orm('sqlite:///%s' % database, logging.WARNING)
    output = ['# Users']
    users = orm.get_users()
    for user in users:
        conversations = orm.get_conversations(user)
        output.append(f'## User {user.id}: {user.username}, conversations: {len(conversations)}')
        for conversation in conversations:
            messages = orm.get_messages(conversation)
            output.append(f'### Conversation {conversation.id}: {conversation.title}, messages: {len(messages)}')
            for message in messages:
                output.append(f'* {message.role}: {message.message}')
    console.print(Markdown("\n".join(output)))

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
        default=DEFAULT_DATABASE,
        action="store",
        help="database filepath",
    )
    parser.add_argument(
        "-u",
        "--users",
        default=DEFAULT_NUM_USERS,
        action="store",
        help="number of users to create, default: %s" % DEFAULT_NUM_USERS,
    )
    parser.add_argument(
        "-n",
        "--conversations",
        default=DEFAULT_NUM_CONVERSATIONS,
        action="store",
        help="number of conversations per user to create, default: %s" % DEFAULT_NUM_CONVERSATIONS,
    )
    parser.add_argument(
        "-m",
        "--messages",
        default=DEFAULT_NUM_MESSAGES,
        action="store",
        help="number of messages per conversation to create, default: %s" % DEFAULT_NUM_MESSAGES,
    )
    args = parser.parse_args()

    db_exists = os.path.exists(args.database)

    if not (args.create or args.test_data or args.print):
        parser.error("At least one of --create, --test-data, --print must be set")

    if args.create:
        if db_exists:
            if args.force:
                console.print("Force specified", style="bold red")
                remove_db(args.database)
                time.sleep(1)
                create_db(args.database)
        else:
            create_db(args.database)

    if args.test_data:
        if db_exists:
            create_test_data(args.database, args.users, args.conversations, args.messages)
        else:
            console.print("Cannot create test data, database not created, use --create to create it", style="bold red")

    if args.print:
        print_data(args.database)

if __name__ == '__main__':
    main()
