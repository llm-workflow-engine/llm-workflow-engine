import os
import importlib.util
import importlib.metadata

from lwe.core.config import Config
from lwe.core.logger import Logger
import lwe.core.util as util

PLUGIN_PREFIX = "lwe_"


class PluginManager:
    def __init__(self, config=None, backend=None, search_path=None, additional_plugins=None):
        additional_plugins = additional_plugins or []
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.backend = backend
        self.search_path = search_path if search_path else self.get_default_plugin_paths()
        self.plugins = {}
        self.package_plugins = {}
        self.plugin_list = list(set(config.get("plugins.enabled") + additional_plugins))
        self.load_package_plugins(self.plugin_list)
        self.load_plugins(self.plugin_list)

    def get_default_plugin_paths(self):
        user_plugin_dirs = (
            self.config.args.plugins_dir
            or util.get_environment_variable_list("plugin_dir")
            or self.config.get("directories.plugins")
        )
        system_plugin_dirs = [
            os.path.join(util.get_package_root(self), "plugins"),
        ]
        plugin_paths = user_plugin_dirs + system_plugin_dirs
        self.log.debug(f"Plugin paths: {plugin_paths}")
        return plugin_paths

    def inject_plugin(self, plugin_name, plugin_class):
        plugin_instance = plugin_class(self.config)
        self.setup_plugin(plugin_name, plugin_instance)
        self.plugins[plugin_name] = plugin_instance

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
        self.log.debug(
            f"Merging plugin {config_key} config, default: {default_config}, user: {user_config}"
        )
        plugin_config = util.merge_dicts(default_config, user_config)
        self.config.set(config_key, plugin_config)

    def load_package_plugins(self, plugin_list):
        self.log.info("Scanning for package plugins")
        entry_point_group = f"{PLUGIN_PREFIX}plugins"
        try:
            entry_points = importlib.metadata.entry_points().select(group=entry_point_group)
        except AttributeError:
            # TODO: Python 3.9 compatibility, remove when we drop support for 3.9.
            entry_points = importlib.metadata.entry_points().get(entry_point_group, [])
        for entry_point in entry_points:
            package_name = entry_point.dist.metadata["Name"]
            plugin_name = util.dash_to_underscore(package_name[len(f"{PLUGIN_PREFIX}plugin_") :])
            if plugin_name in plugin_list:
                try:
                    klass = entry_point.load()
                    plugin_instance = klass(self.config)
                    self.log.info(
                        f"Loaded plugin: {entry_point.name}, from package: {package_name}"
                    )
                    self.package_plugins[plugin_name] = plugin_instance
                except Exception as e:
                    self.log.error(
                        f"Failed to load plugin {entry_point.name}, from package: {package_name}: {e}"
                    )
            else:
                self.log.info(
                    f"Skip loading: {entry_point.name}, from package: {package_name}, reason: not enabled"
                )

    def setup_plugin(self, plugin_name, plugin_instance):
        plugin_instance.set_name(plugin_name)
        plugin_instance.set_backend(self.backend)
        if self.backend.name in plugin_instance.incompatible_backends():
            self.log.error(
                f"Plugin {plugin_name} is incompatible with backend {self.backend.name}, remove it from configuration"
            )
            return False
        self.merge_plugin_config(plugin_instance)
        plugin_instance.setup()
        return True

    def load_plugin(self, plugin_name):
        plugin_instance = None
        for path in self.search_path:
            plugin_file = os.path.join(path, plugin_name + ".py")
            self.log.debug(f"Searching for plugin file {plugin_file}")
            if os.path.exists(plugin_file):
                try:
                    self.log.info(f"Loading plugin {plugin_name} from {plugin_file}")
                    spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    plugin_class_name = util.snake_to_class(plugin_name)
                    plugin_class = getattr(module, plugin_class_name)
                    plugin_instance = plugin_class(self.config)
                    break
                except Exception as e:
                    self.log.error(f"Error loading plugin {plugin_name} from {plugin_file}: {e}")
                    return None
        if plugin_instance is None and plugin_name in self.package_plugins:
            self.log.info(f"Using package plugin for {plugin_name}")
            plugin_instance = self.package_plugins[plugin_name]
        if plugin_instance:
            if not self.setup_plugin(plugin_name, plugin_instance):
                return None
        return plugin_instance

    def get_plugins(self):
        return self.plugins
