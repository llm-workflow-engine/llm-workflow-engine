import os
import yaml

from chatgpt_wrapper.core.config import Config
from chatgpt_wrapper.core.logger import Logger

def parse_preset_dict(content):
    metadata = {}
    customizations = {}
    for key, value in content.items():
        if key.startswith('_'):
            metadata[key[1:]] = value
        else:
            customizations[key] = value
    return metadata, customizations

class PresetManager():
    """
    Manage presets.
    """

    def __init__(self, config=None):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.preset_dirs = self.make_preset_dirs()
        self.load_presets()

    def ensure_preset(self, preset_name):
        if not preset_name:
            return False, None, "No preset name specified"
        self.log.debug(f"Ensuring preset {preset_name} exists")
        if preset_name not in self.presets:
            self.load_presets()
        if preset_name not in self.presets:
            return False, preset_name, f"Preset '{preset_name}' not found"
        message = f"preset {preset_name} exists"
        self.log.debug(message)
        return True, self.presets[preset_name], message

    def make_preset_dirs(self):
        preset_dirs = []
        preset_dirs.append(os.path.join(self.config.config_dir, 'presets'))
        preset_dirs.append(os.path.join(self.config.config_profile_dir, 'presets'))
        for preset_dir in preset_dirs:
            if not os.path.exists(preset_dir):
                os.makedirs(preset_dir)
        return preset_dirs

    def load_presets(self):
        self.log.debug("Loading presets from dirs: %s" % ", ".join(self.preset_dirs))
        self.presets = {}
        try:
            for preset_dir in self.preset_dirs:
                if os.path.exists(preset_dir) and os.path.isdir(preset_dir):
                    self.log.info(f"Processing directory: {preset_dir}")
                    for file_name in os.listdir(preset_dir):
                        if file_name.endswith('.yaml'):
                            self.log.debug(f"Loading YAML file: {file_name}")
                            try:
                                with open(os.path.join(preset_dir, file_name), 'r') as file:
                                    content = yaml.safe_load(file)
                            except Exception as e:
                                self.log.error(f"Error loading YAML file '{file_name}': {e}")
                                continue
                            metadata, customizations = parse_preset_dict(content)
                            preset_name = file_name[:-5]  # Remove '.yaml' extension
                            self.presets[preset_name] = (metadata, customizations)
                            self.log.info(f"Successfully loaded preset: {preset_name}")
                else:
                    message = f"Failed to load presets: Directory '{preset_dir}' not found or not a directory"
                    self.log.error(message)
                    return False, None, message
            return True, self.presets, "Presets successfully loaded"
        except Exception as e:
            message = f"An error occurred while loading presets: {e}"
            self.log.error(message)
            return False, None, message

    def save_preset(self, preset_name, metadata, customizations, preset_dir=None):
        metadata['name'] = preset_name
        preset_data = {f"_{key}": value for key, value in metadata.items()}
        preset_data.update(customizations)
        if preset_dir is None:
            preset_dir = self.preset_dirs[-1]
        file_path = os.path.join(preset_dir, f"{preset_name}.yaml")
        try:
            with open(file_path, 'w') as file:
                yaml.safe_dump(preset_data, file, default_flow_style=False)
            message = f"Successfully saved preset '{preset_name}' to '{file_path}'"
            self.log.info(message)
            return True, file_path, message
        except Exception as e:
            message = f"An error occurred while saving preset '{preset_name}': {e}"
            self.log.error(message)
            return False, None, message

    def delete_preset(self, preset_name, preset_dir=None):
        try:
            if preset_dir is None:
                preset_dir = self.preset_dirs[-1]
            preset_name = f"{preset_name}.yaml" if not preset_name.endswith('.yaml') else preset_name
            file_path = os.path.join(preset_dir, preset_name)
            os.remove(file_path)
            message = f"Successfully deleted preset '{preset_name}' from '{file_path}'"
            self.log.info(message)
            return True, preset_name, message
        except Exception as e:
            message = f"An error occurred while deleting preset '{preset_name}': {e}"
            self.log.error(message)
            return False, None, message
