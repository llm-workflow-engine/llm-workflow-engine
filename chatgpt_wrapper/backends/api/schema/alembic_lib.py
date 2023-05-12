import os

from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

def get_current_dir():
    current_file = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file)
    return current_dir

def set_config(database_url, script_location):
    ini_file = os.path.join(get_current_dir(), 'alembic.ini')
    alembic_cfg = Config(ini_file)
    alembic_cfg.set_main_option('sqlalchemy.url', database_url)
    alembic_cfg.set_main_option("script_location", script_location)
    return alembic_cfg

def is_initialized(engine):
    inspector = inspect(engine)
    return 'alembic_version' in inspector.get_table_names()

def get_current_schema_version(engine):
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version_num FROM alembic_version"))
        return result.scalar()

def get_latest_version(alembic_cfg):
    script = ScriptDirectory.from_config(alembic_cfg)
    return script.get_current_head()

def run_migrations(alembic_cfg):
    database_url = alembic_cfg.get_main_option('sqlalchemy.url')
    engine = create_engine(database_url)
    if not is_initialized(engine):
        stamp_database(alembic_cfg, None)
    command.upgrade(alembic_cfg, 'head')
    return engine

def stamp_database(alembic_cfg, revision='head'):
    command.stamp(alembic_cfg, revision)

def create_revision(name, alembic_cfg):
    command.revision(alembic_cfg, message=name, autogenerate=True)
