import os
import yaml
from alembic import op
import traceback

"""Preset config schema v2

Revision ID: ea7ed165a4ef
Revises: 28ec77033b2e
Create Date: 2023-06-10 11:06:08.384068

"""

# revision identifiers, used by Alembic.
revision = "ea7ed165a4ef"
down_revision = "28ec77033b2e"
branch_labels = None
depends_on = None


def upgrade_preset(preset_path):
    if not preset_path.endswith(".yaml"):
        print(f"Skipping file {preset_path}, not a preset")
        return
    with open(preset_path, "r") as f:
        preset_data = yaml.safe_load(f)
    if "metadata" in preset_data:
        print(f"Metadata key found in preset {preset_path}, preset already migrated, skipping.")
        return
    new_data = {"model_customizations": {}, "metadata": {}}
    for key, value in preset_data.items():
        if key == "_type":
            new_data["metadata"]["provider"] = value
        elif key.startswith("_"):
            new_data["metadata"][key[1:]] = value
        else:
            new_data["model_customizations"][key] = value
    with open(preset_path, "w") as f:
        yaml.safe_dump(new_data, f)
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
