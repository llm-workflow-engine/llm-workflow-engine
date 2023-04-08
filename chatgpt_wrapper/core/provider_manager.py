from chatgpt_wrapper.core.config import Config
from chatgpt_wrapper.core.logger import Logger
from chatgpt_wrapper.core.plugin_manager import PluginManager

class ProviderManager:
    def __init__(self, config, plugin_manager):
        self.config = config or Config()
        self.plugin_manager = plugin_manager or PluginManager(self.config)
        self.log = Logger(self.__class__.__name__, self.config)
        self.provider_plugins = self.get_provider_plugins()

    def get_provider_plugins(self):
        provider_plugins = {k: v for (k, v) in self.plugin_manager.get_plugins().items() if getattr(v, "llm_factory", None)}
        return provider_plugins

    def load_provider(self, provider: str):
        try:
            self.log.debug(f"Attempting to load provider: {provider}")
            provider_instance = self.provider_plugins[provider]
            self.log.debug(f"Found provider: {provider_instance.__class__.__name__}")
        except KeyError:
            message = f"Provider {provider} not found in provider_plugins."
            self.log.error(message)
            return False, None, message
        try:
            self.log.debug(f"Calling llm_factory method on provider {provider_instance.__class__.__name__}")
            llm_class = provider_instance.llm_factory()
            message = f"Successfully loaded provider: {provider}"
            self.log.info(message)
            return True, llm_class, message
        except Exception as e:
            message = f"Error while loading provider {provider}: {str(e)}"
            self.log.error(message)
            return False, None, message
