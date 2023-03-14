import importlib.util
import os

from chatgpt_wrapper.config import Config
from chatgpt_wrapper.logger import Logger
import chatgpt_wrapper.debug as debug
if False:
    debug.console(None)

class PluginManager:
    def __init__(self, config=None, search_path=None):
        self.config = config or Config()
        self.config.set('log.console.level', 'DEBUG')
        self.log = Logger(self.__class__.__name__, self.config)
        self.search_path = search_path
        self.plugins = {}
        self.plugin_list = config.get('plugins.enabled', [])
        self.load_plugins()

    def load_plugins(self, plugin_list):
        for plugin_name in plugin_list:
            plugin_instance = self.load_plugin(plugin_name)
            if plugin_instance is not None:
                self.plugins[plugin_name] = plugin_instance
            else:
                self.log.error(f"Plugin {plugin_name} not found in search path")

    def load_plugin(self, plugin_name):
        for path in self.search_path:
            plugin_file = os.path.join(path, plugin_name + '.py')
            if os.path.exists(plugin_file):
                try:
                    spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    plugin_class_name = plugin_name.capitalize()
                    plugin_class = getattr(module, plugin_class_name)
                    plugin_instance = plugin_class(self.config)
                    return plugin_instance
                except Exception as e:
                    print(f"Error loading plugin {plugin_name} from {plugin_file}: {e}")
                    return None
        return None

    def get_plugins(self):
        return self.plugins
