from abc import ABC, abstractmethod

from chatgpt_wrapper.core.config import Config
from chatgpt_wrapper.core.logger import Logger

class WorkflowBase(ABC):
    def __init__(self, config=None):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)

    def set_name(self, name):
        self.name = name

    def set_backend(self, backend):
        self.backend = backend

    def set_shell(self, shell):
        self.shell = shell

    def make_llm(self, args=None):
        args = args or {}
        return self.backend.make_llm(args)

    def query_llm(self, messages):
        llm = self.make_llm()
        try:
            result = llm(messages)
            result_string = result.content
        except ValueError as e:
            return False, None, e
        return True, result, result_string

class Workflow(WorkflowBase):

    @abstractmethod
    def setup(self):
        pass

    @abstractmethod
    def default_config(self):
        pass

    @abstractmethod
    def run(self):
        pass
