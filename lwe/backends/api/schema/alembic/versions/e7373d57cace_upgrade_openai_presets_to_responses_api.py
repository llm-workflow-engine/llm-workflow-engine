"""Upgrade OpenAI presets to Responses API

Revision ID: e7373d57cace
Revises: 4e642f725923
Create Date: 2025-08-10 10:22:37.929701

"""
from alembic import op
import os
import yaml
import traceback


# revision identifiers, used by Alembic.
revision = 'e7373d57cace'
down_revision = '4e642f725923'
branch_labels = None
depends_on = None


def upgrade_preset(preset_path):
    if not preset_path.endswith(".yaml"):
        print(f"Skipping file {preset_path}, not a preset")
        return
    with open(preset_path, "r") as f:
        preset_data = yaml.safe_load(f)
    if "metadata" in preset_data and "provider" in preset_data["metadata"] and preset_data["metadata"]["provider"] == "chat_openai":
        if "model_customizations" in preset_data and "n" in preset_data["model_customizations"]:
            print(f"'n' setting found in preset {preset_path}, removing.")
            del preset_data["model_customizations"]["n"]
            with open(preset_path, "w") as f:
                yaml.safe_dump(preset_data, f)
                print(f"Upgraded preset file schema: {preset_path}")


def execute_upgrade():
    config_dir = op.get_context().config.attributes["config_dir"]
    main_presets_dir = os.path.join(config_dir, "presets")
    profiles_dir = os.path.join(config_dir, "profiles")
    if os.path.exists(main_presets_dir):
        print("Main presets directory found, processing presets...")
        for preset_file in os.listdir(main_presets_dir):
            upgrade_preset(os.path.join(main_presets_dir, preset_file))
    if os.path.exists(profiles_dir):
        print("Profiles directory found, processing profiles...")
        for profile in os.listdir(profiles_dir):
            profile_dir = os.path.join(profiles_dir, profile)
            presets_dir = os.path.join(profile_dir, "presets")
            if os.path.exists(presets_dir):
                print(f"Presets directory found for profile: {profile}, processing presets...")
                for preset_file in os.listdir(presets_dir):
                    upgrade_preset(os.path.join(presets_dir, preset_file))


def upgrade() -> None:
    try:
        execute_upgrade()
    except Exception as e:
        print(f"Error during migration: {e}")
        print(traceback.format_exc())
        raise e
