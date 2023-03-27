import importlib.util
import os

from chatgpt_wrapper.core.config import Config
from chatgpt_wrapper.core.logger import Logger
import chatgpt_wrapper.core.util as util

class PluginManager:
    def __init__(self, config=None, backend=None, search_path=None):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.backend = backend
        self.search_path = search_path if search_path else self.get_default_plugin_paths()
        self.plugins = {}
        self.plugin_list = config.get('plugins.enabled')
        self.load_plugins(self.plugin_list)

    def get_default_plugin_paths(self):
        package_root = os.path.join(util.get_package_root(self), 'plugins')
        self.log.debug(f"Package root: {package_root}")
        plugin_paths = [
            package_root,
            os.path.join(self.config.config_dir, 'plugins'),
            os.path.join(self.config.config_profile_dir, 'plugins'),
        ]
        return plugin_paths

    def load_plugins(self, plugin_list):
        for plugin_name in plugin_list:
            plugin_instance = self.load_plugin(plugin_name)
            if plugin_instance is not None:
                self.plugins[plugin_name] = plugin_instance
            else:
                self.log.error(f"Plugin {plugin_name} not found in search path")

    def merge_plugin_config(self, plugin_instance):
        config_key = f"plugins.{plugin_instance.name}"
        default_config = plugin_instance.default_config()
        user_config = self.config.get(config_key) or {}
        self.log.debug(f"Merging plugin {config_key} config, default: {default_config}, user: {user_config}")
        plugin_config = util.merge_dicts(default_config, user_config)
        self.config.set(config_key, plugin_config)

    def load_plugin(self, plugin_name):
        for path in self.search_path:
            plugin_file = os.path.join(path, plugin_name + '.py')
            self.log.debug(f"Searching for plugin file {plugin_file}")
            if os.path.exists(plugin_file):
                try:
                    self.log.info(f"Loading plugin {plugin_name} from {plugin_file}")
                    spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    plugin_class_name = plugin_name.capitalize()
                    plugin_class = getattr(module, plugin_class_name)
                    plugin_instance = plugin_class(self.config)
                    plugin_instance.set_name(plugin_name)
                    plugin_instance.set_backend(self.backend)
                    self.merge_plugin_config(plugin_instance)
                    plugin_instance.setup()
                    return plugin_instance
                except Exception as e:
                    self.log.error(f"Error loading plugin {plugin_name} from {plugin_file}: {e}")
                    return None
        return None

    def get_plugins(self):
        return self.plugins
