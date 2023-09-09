from lwe.core.config import Config
from lwe.core.logger import Logger
from lwe.core import constants
from lwe.core.plugin_manager import PluginManager


class ProviderManager:
    def __init__(self, config, plugin_manager):
        self.config = config or Config()
        self.plugin_manager = plugin_manager or PluginManager(self.config)
        self.log = Logger(self.__class__.__name__, self.config)
        self.provider_plugins = self.get_provider_plugins()

    def get_provider_plugins(self):
        provider_plugins = {
            k: v
            for (k, v) in self.plugin_manager.get_plugins().items()
            if v.plugin_type == "provider"
        }
        return provider_plugins

    def full_name(self, name):
        if name[:9] != constants.PROVIDER_PREFIX:
            name = f"{constants.PROVIDER_PREFIX}{name}"
        return name

    def load_provider(self, provider_name: str):
        try:
            self.log.debug(f"Attempting to load provider: {provider_name}")
            provider = self.provider_plugins[self.full_name(provider_name)]
            self.log.debug(f"Found provider: {provider.__class__.__name__}")
        except KeyError:
            message = f"Provider {provider_name} not found in provider_plugins."
            self.log.error(message)
            return False, None, message
        message = f"Successfully loaded provider: {provider_name}"
        self.log.info(message)
        return True, provider, message

    def get_provider_from_name(self, provider_name):
        full_name = self.full_name(provider_name)
        return self.provider_plugins[full_name] if full_name in self.provider_plugins else None
