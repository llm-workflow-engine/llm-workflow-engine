from abc import abstractmethod

from chatgpt_wrapper.core.plugin import Plugin

class ProviderBase(Plugin):

    @property
    def plugin_type(self):
        return 'provider'

    def incompatible_backends(self):
        return [
            'chatgpt-browser',
        ]

    def setup(self):
        pass

    def default_config(self):
        return {}

class Provider(ProviderBase):

    @abstractmethod
    def llm_factory(self):
        pass
