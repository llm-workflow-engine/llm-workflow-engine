from abc import ABC, abstractmethod

from chatgpt_wrapper.config import Config
from chatgpt_wrapper.logger import Logger
import chatgpt_wrapper.debug as debug
if False:
    debug.console(None)

class PluginBase(ABC):
    def __init__(self, config=None):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)

    @abstractmethod
    def setup(self):
        pass

    def set_backend(self, backend):
        self.backend = backend

    def set_shell(self, shell):
        self.shell = shell

    def get_shell_completions(self, _base_shell_completions):
        pass

class Plugin(PluginBase):

    @abstractmethod
    def setup(self):
        pass

