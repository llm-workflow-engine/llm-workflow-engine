from abc import ABC, abstractmethod
import datetime

from lwe.core.config import Config
from lwe.core.logger import Logger
from lwe.core.cache_manager import CacheManager

PLUGIN_CACHE_API_VERSION = 1


class PluginBase:
    def __init__(self, config=None, cache_manager=None):
        self.config = config or Config()
        self.cache_manager = cache_manager or CacheManager(self.config)
        self.log = Logger(self.__class__.__name__, self.config)

    @property
    def plugin_type(self):
        return "plugin"

    @property
    def description(self):
        if self.__class__.__doc__:
            return self.__class__.__doc__.strip().split("\n")[0]
        return ""

    @property
    def plugin_cache_filename(self):
        return f"{self.name}.yaml"

    def write_plugin_cache_file(self, data):
        data["api_version"] = PLUGIN_CACHE_API_VERSION
        data["last_updated"] = datetime.datetime.now().isoformat()
        self.cache_manager.cache_set(self.plugin_cache_filename, data)

    def set_name(self, name):
        self.name = name

    def set_backend(self, backend):
        self.backend = backend

    def set_shell(self, shell):
        self.shell = shell

    def get_shell_completions(self, _base_shell_completions):  # noqa B027
        pass

    def incompatible_backends(self):
        return []

    def make_llm(self, args=None):
        args = args or {}
        return self.backend.make_llm(args)

    def query_llm(self, messages):
        llm = self.make_llm()
        try:
            result = llm.invoke(messages)
            result_string = result.content
        except ValueError as e:
            return False, None, e
        return True, result, result_string


class Plugin(PluginBase, ABC):
    @abstractmethod
    def setup(self):
        pass

    @abstractmethod
    def default_config(self):
        pass
