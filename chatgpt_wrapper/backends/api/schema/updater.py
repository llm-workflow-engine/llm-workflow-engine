#!/usr/bin/env python

import os
import sys
import traceback
import argparse

from sqlalchemy import create_engine

from chatgpt_wrapper.core.config import Config
from chatgpt_wrapper.core.logger import Logger
import chatgpt_wrapper.backends.api.schema.alembic_lib as alembic
from chatgpt_wrapper.core import util

class SchemaUpdater:
    def __init__(self, config=None):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.database_url = self.config.get('database')
        self.script_location = os.path.join(util.get_package_root(self), 'backends', 'api', 'schema', 'alembic')
        self.alembic_cfg = alembic.set_config(self.database_url, self.script_location)
        self.log.debug("Initialized SchemaUpdater with database URL: %s, script location: %s", self.database_url, self.script_location)

    def confirm_upgrade(self):
        answer = input("Do you want to upgrade the database schema? (yes/no): ")
        return answer.lower() == "yes"

    def init_alembic(self):
        alembic.stamp_database(self.alembic_cfg)

    def update_schema(self):
        try:
            engine = create_engine(self.database_url)
            initialized = alembic.is_initialized(engine)
            current_version = None if not initialized else alembic.get_current_schema_version(engine)
            latest_version = alembic.get_latest_version(self.alembic_cfg)

            self.log.debug("Current schema version: %s", current_version)
            self.log.debug("Latest schema version: %s", latest_version)

            if not initialized or current_version != latest_version:
                message = "Database schema is out of date."
                self.log.warning(message)
                util.print_status_message(False, message)
                util.print_status_message(False, "It is highly recommended to backup your database prior to upgrading.")
                util.print_status_message(False, f"Database: {self.database_url}")
                if self.confirm_upgrade():
                    message = "Upgrading the schema..."
                    self.log.info(message)
                    util.print_status_message(True, message, style="bold blue")
                    alembic.run_migrations(self.alembic_cfg)
                    message = "Database schema has been successfully upgraded."
                    self.log.info(message)
                    util.print_status_message(True, message)
                else:
                    message = "Database schema upgrade aborted."
                    self.log.warning(message)
                    util.print_status_message(False, message)
                    sys.exit(0)
            else:
                self.log.info("Database schema is up to date.")
        except Exception as e:
            self.log.error("Error during schema update process: %s", str(e))
            traceback_str = traceback.format_exc()
            self.log.error(f"Stack trace: {traceback_str}")
            util.print_status_message(False, "An error occurred during the schema update process. Please check the logs.")

    def add_revision(self, name):
        alembic.create_revision(name, self.alembic_cfg)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Schema Updater")
    parser.add_argument("--add", required=True, help="Create a new migration revision", type=str)
    args = parser.parse_args()
    config = Config()
    config.set('debug.log.enabled', True)
    config.set('console.log.level', 'debug')
    schema_updater = SchemaUpdater()
    if args.add:
        schema_updater.add_revision(args.add)
