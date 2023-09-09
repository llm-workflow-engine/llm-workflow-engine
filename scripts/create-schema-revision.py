#!/usr/bin/env python

import argparse
import logging
import os
import sys
from pathlib import Path
from alembic import command
from alembic.config import Config as AlembicConfig
from lwe.core.config import Config
import lwe.core.util as util

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_database_url():
    config = Config()
    database = config.get("database")
    return database


def create_schema_revision(message, database_url=None):
    if not database_url:
        logger.info("No database url specified, using default.")
        database_url = get_database_url()
    logger.info(
        f"Creating schema revision with message: {message!r}, database_url: {database_url!r}"
    )

    alembic_cfg = AlembicConfig()
    script_path = Path(__file__).resolve().parent
    root_path = script_path.parent
    logger.info(f"Root path found: {root_path}")
    ini_file = os.path.join(root_path, "lwe", "backends", "api", "schema", "alembic.ini")
    logger.info("Creating alembic config using .ini: %s", ini_file)
    alembic_cfg = AlembicConfig(ini_file)
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)

    try:
        logger.info("Starting schema revision generation...")
        command.revision(alembic_cfg, message, autogenerate=True)
        logger.info("Schema revision created successfully.")
        util.print_markdown(
            """
## To dump and re-import data into a fresh schema:

 * `sudo apt install libsqlite3-mod-impexp`
 * *...open original Sqlite database...*
 * `.load libsqlite3_mod_impexp`
 * `select export_sql('/tmp/dump.sql','1');`
 * *...backup original database, then delete it...*
 * *...create fresh database, and open it in Sqlite...*
 * `.read /tmp/dump.sql`
          """
        )
    except Exception as e:
        logger.error(f"Error creating schema revision: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a new schema revision by comparing the updated schema with the original schema in a reference database."
    )
    parser.add_argument(
        "-m", "--message", required=True, help="Human-readable message for the revision"
    )
    parser.add_argument(
        "-d", "--database-url", help="SQLAlchemy connection string to the reference database"
    )

    args = parser.parse_args()

    create_schema_revision(args.message, args.database_url)
