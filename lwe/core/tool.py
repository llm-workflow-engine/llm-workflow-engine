from abc import abstractmethod

import yaml

from pathlib import Path

from lwe.core.config import Config
from lwe.core.logger import Logger
from lwe.core.doc_parser import func_to_openai_tool_spec


class Tool:
    def __init__(self, config):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)

    def set_name(self, name):
        self.name = name

    def set_filepath(self, filepath):
        self.filepath = filepath

    def get_config(self):
        filepath = Path(self.filepath)
        config_filepath = filepath.with_suffix(".config.yaml")
        if config_filepath.is_file():
            try:
                self.log.debug(
                    f"Loading configuration for {self.name} from filepath: {config_filepath}"
                )
                with open(config_filepath, "r") as config_file:
                    config = yaml.safe_load(config_file)
                self.log.debug(f"Loaded YAML configuration for {self.name}: {config}")
                return config
            except Exception as e:
                self.log.error(f"Error loading configuration for {self.name}: {str(e)}")
                raise ValueError(f"Failed to load configuration file for {self.name}") from e
        return func_to_openai_tool_spec(self.name, self.__call__)

    @abstractmethod
    def __call__(self, **kwargs):
        pass
