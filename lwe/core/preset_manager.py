import os
import copy
import yaml

from lwe.core.config import Config
from lwe.core.logger import Logger
import lwe.core.util as util


def parse_llm_dict(content):
    metadata = {}
    customizations = {}
    for key, value in content.items():
        if key == "_type":
            metadata["provider"] = value
        elif key.startswith("_"):
            metadata[key[1:]] = value
        else:
            customizations[key] = value
    return metadata, customizations


class PresetManager:
    """
    Manage presets.
    """

    def __init__(self, config=None, additional_presets=None):
        self.config = config or Config()
        self.additional_presets = additional_presets or {}
        self.log = Logger(self.__class__.__name__, self.config)
        self.user_preset_dirs = (
            self.config.args.presets_dir
            or util.get_environment_variable_list("preset_dir")
            or self.config.get("directories.presets")
        )
        self.make_user_preset_dirs()
        self.system_preset_dirs = [
            os.path.join(util.get_package_root(self), "presets"),
        ]
        self.all_preset_dirs = self.system_preset_dirs + self.user_preset_dirs
        self.load_presets()

    def ensure_preset(self, preset_name):
        if not preset_name:
            return False, None, "No preset name specified"
        self.log.debug(f"Ensuring preset {preset_name} exists")
        if preset_name not in self.presets:
            self.load_presets()
        if preset_name not in self.presets:
            return False, preset_name, f"Preset {preset_name!r} not found"
        message = f"preset {preset_name} exists"
        self.log.debug(message)
        return True, self.presets[preset_name], message

    def make_user_preset_dirs(self):
        for preset_dir in self.user_preset_dirs:
            if not os.path.exists(preset_dir):
                os.makedirs(preset_dir)

    def parse_preset_dict(self, content):
        return content["metadata"], content["model_customizations"]

    def user_metadata_fields(self):
        return {
            "description": str,
            "system_message": str,
            "max_submission_tokens": int,
            "return_on_tool_call": bool,
            "return_on_tool_response": bool,
        }

    def load_test_preset(self):
        if self.config.profile == "test":
            self.log.debug("Test profile detected, loading test preset")
            test_preset = (
                {
                    "description": "Testing preset",
                    "name": "test",
                    "provider": "fake_llm",
                    "filepath": "",
                },
                {},
            )
            self.presets["test"] = test_preset
            test_preset_2 = (
                {
                    "description": "Testing preset 2",
                    "name": "test_2",
                    "provider": "fake_llm",
                    "filepath": "",
                },
                {
                    "model_name": "gpt-4o",
                },
            )
            self.presets["test_2"] = test_preset_2

    def load_presets(self):
        self.log.debug("Loading presets from dirs: %s" % ", ".join(self.all_preset_dirs))
        self.presets = copy.deepcopy(self.additional_presets)
        self.load_test_preset()
        try:
            for preset_dir in self.all_preset_dirs:
                if os.path.exists(preset_dir) and os.path.isdir(preset_dir):
                    self.log.info(f"Processing directory: {preset_dir}")
                    for file_name in os.listdir(preset_dir):
                        if file_name.endswith(".yaml"):
                            self.log.debug(f"Loading YAML file: {file_name}")
                            try:
                                filepath = os.path.join(preset_dir, file_name)
                                with open(filepath, "r") as file:
                                    content = yaml.safe_load(file)
                            except Exception as e:
                                self.log.error(f"Error loading YAML file {file_name!r}: {e}")
                                continue
                            metadata, customizations = self.parse_preset_dict(content)
                            metadata["filepath"] = filepath
                            preset_name = file_name[:-5]  # Remove '.yaml' extension
                            self.presets[preset_name] = (metadata, customizations)
                            self.log.info(f"Successfully loaded preset: {preset_name}")
                else:
                    message = f"Failed to load presets: Directory {preset_dir!r} not found or not a directory"
                    self.log.error(message)
                    return False, None, message
            return True, self.presets, "Presets successfully loaded"
        except Exception as e:
            message = f"An error occurred while loading presets: {e}"
            self.log.error(message)
            return False, None, message

    def save_preset(self, preset_name, metadata, customizations, preset_dir=None):
        metadata["name"] = preset_name
        preset_data = {
            "metadata": metadata,
            "model_customizations": customizations,
        }
        if preset_dir is None:
            preset_dir = self.user_preset_dirs[-1]
        file_path = os.path.join(preset_dir, f"{preset_name}.yaml")
        try:
            with open(file_path, "w") as file:
                yaml.safe_dump(preset_data, file, default_flow_style=False)
            message = f"Successfully saved preset {preset_name!r} to {file_path!r}"
            self.log.info(message)
            return True, file_path, message
        except Exception as e:
            message = f"An error occurred while saving preset {preset_name!r}: {e}"
            self.log.error(message)
            return False, None, message

    def delete_preset(self, preset_name, preset_dir=None):
        try:
            if preset_dir is None:
                preset_dir = self.user_preset_dirs[-1]
            preset_name = (
                f"{preset_name}.yaml" if not preset_name.endswith(".yaml") else preset_name
            )
            file_path = os.path.join(preset_dir, preset_name)
            os.remove(file_path)
            message = f"Successfully deleted preset {preset_name!r} from {file_path!r}"
            self.log.info(message)
            return True, preset_name, message
        except Exception as e:
            message = f"An error occurred while deleting preset {preset_name!r}: {e}"
            self.log.error(message)
            return False, None, message

    def is_system_preset(self, filepath):
        for dir in self.system_preset_dirs:
            if filepath.startswith(dir):
                return True
        return False
