"""tools-migration

Revision ID: 4e642f725923
Revises: cc8f2aecf9ff
Create Date: 2024-05-16 14:40:13.707040

"""
import os
from alembic import op
import sqlalchemy as sa
import json
import traceback


# revision identifiers, used by Alembic.
revision = '4e642f725923'
down_revision = 'cc8f2aecf9ff'
branch_labels = None
depends_on = None


def print_deprectated_functions_dir_migration_path(dir):
    parent_dir = os.path.dirname(dir)
    print(f" - {dir} -> {os.path.join(parent_dir, 'tools')}")


def print_directory_deprecation_warnings():
    config_dir = op.get_context().config.attributes["config_dir"]
    main_functions_dir = os.path.join(config_dir, "functions")
    profiles_dir = os.path.join(config_dir, "profiles")
    print("The following directories are deprecated, and should be renamed from 'functions' to 'tools':")
    if os.path.exists(main_functions_dir):
        print_deprectated_functions_dir_migration_path(main_functions_dir)
    if os.path.exists(profiles_dir):
        for profile in os.listdir(profiles_dir):
            profile_dir = os.path.join(profiles_dir, profile)
            functions_dir = os.path.join(profile_dir, "functions")
            if os.path.exists(functions_dir):
                print_deprectated_functions_dir_migration_path(functions_dir)


def print_deprecation_warnings():
    print_directory_deprecation_warnings()


def execute_upgrade():
    print_deprecation_warnings()


def upgrade() -> None:
    try:
        execute_upgrade()
    except Exception as e:
        print(f"Error during migration: {e}")
        print(traceback.format_exc())
        raise e
