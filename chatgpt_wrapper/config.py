import os
import yaml
import platform
import logging

DEFAULT_CONFIG_DIR = 'chatgpt-wrapper'
DEFAULT_CONFIG = {
    'profile': 'default',
    'database': '/tmp/chatgpt-test.db',
    'model': 'default',
    'browser': {
        'provider': 'firefox',
        'debug': False,
    },
    'log': {
        'enabled': True,
        'file': 'chatgpt.log',
        'level': {
            'console': 'error',
            'file': 'debug',
        },
    },
    'debug': {
        'log': {
            'enabled': False,
            'file': 'chatgpt-debug.log',
        },
    },
}

class Config:
    def __init__(self, profile=DEFAULT_CONFIG['profile'], config_dir=None, data_dir=None):
        self.system = platform.system()
        if config_dir:
            self.config_dir = config_dir
        else:
            self.config_dir = self._default_config_dir()
        if data_dir:
            self.data_dir = data_dir
        else:
            self.data_dir = self._default_data_dir()
        self.config = self._load_config()

    def _default_config_dir(self):
        if self.system == "Windows":
            return os.path.join(os.environ["APPDATA"], DEFAULT_CONFIG_DIR)
        elif self.system == "Darwin":
            return os.path.join(os.path.expanduser("~"), "Library", "Application Support", DEFAULT_CONFIG_DIR)
        else:
            return os.path.join(os.path.expanduser("~"), ".config", DEFAULT_CONFIG_DIR)

    def _default_data_dir(self):
        if self.system == "Windows":
            data_dir = os.path.join(os.environ["LOCALAPPDATA"], DEFAULT_CONFIG_DIR)
        else:
            data_dir = os.path.join(os.path.expanduser("~"), ".local", "share", DEFAULT_CONFIG_DIR)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        return data_dir

    def _load_config(self, profile):
        config_file = os.path.join(self.config_dir, profile + ".yaml")
        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
            self.config = self._merge_configs(self.DEFAULT_CONFIG, config)
        except FileNotFoundError:
            self.config = self.DEFAULT_CONFIG
        self._transform_config()

    def _transform_config(self):
        level = self.config['log']['level']
        self.config['log']['level']['console'] = getattr(logging, level['console'].upper())
        self.config['log']['level']['file'] = getattr(logging, level['file'].upper())

    def _merge_configs(self, default, config):
        if isinstance(default, dict) and isinstance(config, dict):
            for key, value in default.items():
                if key not in config:
                    config[key] = value
                else:
                    config[key] = self._merge_configs(value, config[key])
        return config

    def get(self, *keys, default=None):
        config = self.config
        for key in keys:
            if not isinstance(config, dict):
                raise TypeError(f"Key '{key}' not found or value is not a dictionary")
            if key in config:
                config = config[key]
            else:
                return default
        return config
