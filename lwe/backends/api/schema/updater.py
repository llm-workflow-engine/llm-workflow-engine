#!/usr/bin/env python

import os
import sys
import traceback
import argparse

from alembic.config import Config as AlembicConfig
from alembic import command
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect

from lwe.core.config import Config
from lwe.core.logger import Logger
from lwe.core import util

from lwe.backends.api.orm import Orm


class SchemaUpdater:
    def __init__(self, config=None, orm=None):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.database_url = self.config.get("database")
        self.alembic_cfg = self.set_config()
        self.orm = orm or Orm(self.config)
        self.engine = self.orm.engine
        self.versioning_initialized = self.is_versioning_initialized()
        self.log.debug("Initialized SchemaUpdater with database URL: %s", self.database_url)

    def set_config(self):
        ini_file = os.path.join(util.get_file_directory(), "alembic.ini")
        self.log.debug("Creating alembic config using .ini: %s", ini_file)
        alembic_cfg = AlembicConfig(ini_file)
        alembic_cfg.set_main_option("sqlalchemy.url", self.database_url)
        alembic_cfg.attributes["config_dir"] = self.config.config_dir
        alembic_cfg.attributes["config_profile_dir"] = self.config.config_profile_dir
        alembic_cfg.attributes["data_dir"] = self.config.data_dir
        alembic_cfg.attributes["data_profile_dir"] = self.config.data_profile_dir
        return alembic_cfg

    def is_versioning_initialized(self):
        inspector = inspect(self.engine)
        initialized = "alembic_version" in inspector.get_table_names()
        self.log.debug("Schema versioning initialized: %s", initialized)
        return initialized

    def get_current_schema_version(self):
        current_revision = None
        if self.versioning_initialized:
            with self.engine.connect() as connection:
                migration_context = MigrationContext.configure(connection)
                current_revision = migration_context.get_current_revision()
        self.log.info("Current schema version for database: %s", current_revision)
        return current_revision

    def get_latest_version(self):
        script = ScriptDirectory.from_config(self.alembic_cfg)
        latest_version = script.get_current_head()
        self.log.info("Latest schema version: %s", latest_version)
        return latest_version

    def run_migrations(self):
        self.log.debug("Running migrations")
        if not self.versioning_initialized:
            self.log.info("Initializing alembic versioning")
            self.stamp_database(None)
        command.upgrade(self.alembic_cfg, "head")

    def stamp_database(self, revision="head"):
        self.log.debug("Stamping database with version: %s", revision)
        command.stamp(self.alembic_cfg, revision)

    def confirm_upgrade(self):
        answer = input("Do you want to upgrade the schema? (yes/no): ")
        return answer.lower() == "yes"

    def init_alembic(self):
        self.stamp_database()

    def update_schema(self):
        try:
            current_version = self.get_current_schema_version()
            latest_version = self.get_latest_version()
            if not self.versioning_initialized or current_version != latest_version:
                message = "Schema is out of date."
                self.log.warning(message)
                util.print_status_message(False, message)
                util.print_status_message(
                    False,
                    "It is highly recommended to backup your database and configruation directory prior to upgrading.",
                )
                util.print_status_message(False, f"Database: {self.database_url}")
                util.print_status_message(
                    False, f"Configuration directory: {self.config.config_dir}"
                )
                if self.confirm_upgrade():
                    upgrading_message = "Upgrading the schema..."
                    self.log.info(upgrading_message)
                    util.print_status_message(True, upgrading_message, style="bold blue")
                    self.run_migrations()
                    upgraded_message = "Schema has been successfully upgraded."
                    self.log.info(upgraded_message)
                    util.print_status_message(True, upgraded_message)
                else:
                    message = "Schema upgrade aborted."
                    self.log.warning(message)
                    util.print_status_message(False, message)
                    sys.exit(0)
            else:
                self.log.info("Schema is up to date.")
        except Exception as e:
            self.log.error("Error during schema update process: %s", str(e))
            traceback_str = traceback.format_exc()
            self.log.error(f"Stack trace: {traceback_str}")
            util.print_status_message(
                False, "An error occurred during the schema update process. Please check the logs."
            )
            sys.exit(0)

    def add_revision(self, name):
        command.revision(self.alembic_cfg, message=name, autogenerate=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Schema Updater")
    parser.add_argument("--add", required=True, help="Create a new migration revision", type=str)
    args = parser.parse_args()
    config = Config()
    config.set("debug.log.enabled", True)
    config.set("console.log.level", "debug")
    schema_updater = SchemaUpdater(config)
    if args.add:
        schema_updater.add_revision(args.add)
