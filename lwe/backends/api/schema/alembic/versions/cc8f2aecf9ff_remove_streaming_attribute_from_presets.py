import os
import yaml
from alembic import op
import traceback

"""Remove streaming attribute from presets

Revision ID: cc8f2aecf9ff
Revises: c7d7803302a9
Create Date: 2023-08-15 11:34:18.866737

"""

# revision identifiers, used by Alembic.
revision = "cc8f2aecf9ff"
down_revision = "c7d7803302a9"
branch_labels = None
depends_on = None


def upgrade_preset(preset_path):
    if not preset_path.endswith(".yaml"):
        print(f"Skipping file {preset_path}, not a preset")
        return
    with open(preset_path, "r") as f:
        preset_data = yaml.safe_load(f)
    if "model_customizations" in preset_data and "streaming" in preset_data["model_customizations"]:
        print(f"streaming setting found in preset {preset_path}, removing.")
        del preset_data["model_customizations"]["streaming"]
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
