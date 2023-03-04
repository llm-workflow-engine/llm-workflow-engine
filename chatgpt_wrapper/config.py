import os
import yaml
import platform

import chatgpt_wrapper.constants as constants

class Config:
    def __init__(self, config_dir=None, data_dir=None, profile=constants.DEFAULT_PROFILE, config={}):
        self.system = platform.system()
        if config_dir:
            if not os.path.exists(config_dir):
                raise FileNotFoundError(f"The config directory '{config_dir}' does not exist.")
            self.config_dir = config_dir
        else:
            self.config_dir = self._default_config_dir()
        if data_dir:
            if not os.path.exists(data_dir):
                raise FileNotFoundError(f"The data directory '{data_dir}' does not exist.")
            self.data_dir = data_dir
        else:
            self.data_dir = self._default_data_dir()
        self.profile = profile
        self.config = self._merge_configs(constants.DEFAULT_CONFIG, config)
        self._transform_config()

    def _default_config_dir(self):
        if self.system == "Windows":
            return os.path.join(os.environ["APPDATA"], constants.DEFAULT_CONFIG_DIR)
        elif self.system == "Darwin":
            return os.path.join(os.path.expanduser("~"), "Library", "Application Support", constants.DEFAULT_CONFIG_DIR)
        else:
            return os.path.join(os.path.expanduser("~"), ".config", constants.DEFAULT_CONFIG_DIR)

    def _default_data_dir(self):
        if self.system == "Windows":
            data_dir = os.path.join(os.environ["LOCALAPPDATA"], constants.DEFAULT_CONFIG_DIR)
        else:
            data_dir = os.path.join(os.path.expanduser("~"), ".local", "share", constants.DEFAULT_CONFIG_DIR)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        return data_dir

    def load_from_file(self, profile=None):
        profile = profile or self.profile
        config_file = os.path.join(self.config_dir, profile + ".yaml")
        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
            self.config = self._merge_configs(constants.DEFAULT_CONFIG, config)
        except FileNotFoundError:
            self.config = constants.DEFAULT_CONFIG
        self._transform_config()

    def _transform_config(self):
        self.set('log.console.level', self.get('log.console.level').upper(), False)
        self.set('debug.log.level', self.get('debug.log.level').upper(), False)

    def _merge_configs(self, default, config):
        if isinstance(default, dict) and isinstance(config, dict):
            for key, value in default.items():
                if key not in config:
                    config[key] = value
                else:
                    config[key] = self._merge_configs(value, config[key])
        return config

    def get(self, keys=None, config=None):
        config = config or self.config
        if keys:
            if isinstance(keys, str):
                keys = keys.split(".")
            for key in keys:
                if key in config:
                    config = config[key]
                else:
                    return self.get(keys, constants.DEFAULT_CONFIG)
        return config

    def set(self, keys, value, transform=True):
        if isinstance(keys, str):
            keys = keys.split(".")
        config = self.config
        for key in keys[:-1]:
            config = config.setdefault(key, {})
        config[keys[-1]] = value
        if transform:
            self._transform_config()
