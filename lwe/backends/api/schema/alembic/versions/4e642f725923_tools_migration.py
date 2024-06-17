"""tools-migration

Revision ID: 4e642f725923
Revises: cc8f2aecf9ff
Create Date: 2024-05-16 14:40:13.707040

"""

import os
import json
import traceback
import random
import string
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker, declarative_base
import lwe.core.util as util

# revision identifiers, used by Alembic.
revision = "4e642f725923"
down_revision = "cc8f2aecf9ff"
branch_labels = None
depends_on = None

Base = declarative_base()


class Message(Base):
    __tablename__ = "message"
    id = sa.Column(sa.Integer, primary_key=True)
    conversation_id = sa.Column(sa.Integer, nullable=False)
    role = sa.Column(sa.String, nullable=False)
    message = sa.Column(sa.String, nullable=False)
    message_type = sa.Column(sa.String, nullable=False)
    message_metadata = sa.Column(sa.String)
    model = sa.Column(sa.String, nullable=False)
    provider = sa.Column(sa.String, nullable=False)
    preset = sa.Column(sa.String, nullable=False)
    created_time = sa.Column(sa.DateTime, nullable=False)


def generate_tool_call_id(length=24):
    return "call_" + "".join(random.choices(string.ascii_letters + string.digits, k=length))


def print_deprectated_functions_dir_migration_path(dir):
    parent_dir = os.path.dirname(dir)
    util.print_status_message(False, f" - {dir} -> {os.path.join(parent_dir, 'tools')}")


def print_directory_deprecation_warnings():
    config_dir = op.get_context().config.attributes["config_dir"]
    main_functions_dir = os.path.join(config_dir, "functions")
    profiles_dir = os.path.join(config_dir, "profiles")
    util.print_status_message(
        False,
        "The following directories are deprecated, and should be renamed from 'functions' to 'tools':",
    )
    if os.path.exists(main_functions_dir):
        print_deprectated_functions_dir_migration_path(main_functions_dir)
    if os.path.exists(profiles_dir):
        for profile in os.listdir(profiles_dir):
            profile_dir = os.path.join(profiles_dir, profile)
            functions_dir = os.path.join(profile_dir, "functions")
            if os.path.exists(functions_dir):
                print_deprectated_functions_dir_migration_path(functions_dir)


def print_breaking_changes():
    print()
    print()
    util.print_status_message(False, "BREAKING CHANGES:")
    util.print_status_message(
        False,
        "The configuration of 'functions' in presets has changed to a 'tools' configuration, see https://github.com/llm-workflow-engine/llm-workflow-engine/issues/345 for migration instructions.",
    )


def print_deprecation_warnings():
    print()
    print()
    util.print_status_message(False, "DEPRECATION WARNINGS:")
    util.print_status_message(False, "'/functions' CLI command is now '/tools'")
    util.print_status_message(
        False, "Environment variable 'LWE_FUNCTION_DIR' has been renamed to 'LWE_TOOL_DIR'."
    )
    util.print_status_message(
        False,
        "Configuration variable 'directories.functions' has been renamed to 'directories.tools'.",
    )
    print_directory_deprecation_warnings()


def upgrade_function_calls_to_tool_calls():
    bind = op.get_bind()
    Session = sessionmaker(bind=bind)
    session = Session()
    messages = (
        session.query(Message)
        .filter(Message.message_type.in_(["function_call", "function_response"]))
        .all()
    )
    tool_call_id = None
    if len(messages) > 0:
        util.print_status_message(
            True, "FOUND FUNCTION CALLS IN THE DATABASE, UPDATING TO TOOL CALLS..."
        )
    for message in messages:
        if message.message_type == "function_call":
            tool_call_id = generate_tool_call_id()
            message_content = json.loads(message.message)
            args = message_content.pop("arguments", {})
            message_content["args"] = args
            message_content["id"] = tool_call_id
            message.message = json.dumps([message_content])
            message.message_type = "tool_call"
            util.print_status_message(
                True,
                f"Updated function_call to tool_call for message ID {message.id}: tool_call_id={tool_call_id}",
                style="bold blue",
            )
        elif message.message_type == "function_response":
            message_metadata = (
                json.loads(message.message_metadata) if message.message_metadata else {}
            )
            message_metadata["id"] = tool_call_id
            message.role = "tool"
            message.message_type = "tool_response"
            message.message_metadata = json.dumps(message_metadata)
            util.print_status_message(
                True,
                f"Updated function_response to tool_response for message ID {message.id}: tool_call_id={tool_call_id}",
                style="bold blue",
            )
        session.add(message)
    session.commit()


def execute_upgrade():
    upgrade_function_calls_to_tool_calls()
    print_breaking_changes()
    print_deprecation_warnings()


def upgrade() -> None:
    try:
        execute_upgrade()
    except Exception as e:
        print(f"Error during migration: {e}")
        print(traceback.format_exc())
        raise e
