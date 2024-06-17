from abc import ABC, abstractmethod

from lwe.core.config import Config
from lwe.core.logger import Logger


class PluginBase:
    def __init__(self, config=None):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)

    @property
    def plugin_type(self):
        return "plugin"

    @property
    def description(self):
        if self.__class__.__doc__:
            return self.__class__.__doc__.strip().split("\n")[0]
        return ""

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
