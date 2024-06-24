import os
import json
import yaml

from lwe.core.config import Config
from lwe.core.logger import Logger
import lwe.core.util as util


class CacheManager:
    """
    Manage cache entries.
    """

    def __init__(self, config=None):
        """
        Initializes the class with the given configuration.

        :param config: Configuration settings. If not provided, a default Config object is used.
        :type config: Config, optional
        """
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.cache_dirs = (
            self.config.args.cache_dir
            or util.get_environment_variable_list("cache_dir")
            or self.config.get("directories.cache")
        )
        self.make_cache_dirs()

    def make_cache_dirs(self):
        """
        Create directories for the cache if they do not exist.

        :return: None
        """
        for cache_dir in self.cache_dirs:
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)

    def load_file(self, file):
        """
        Load a file from the cache.

        :param file: The file to load.
        :return: A tuple containing a success indicator, the loaded content, and a message.
        """
        try:
            with open(file, "r") as f:
                content = f.read()
            if file.endswith(".yaml"):
                content = yaml.safe_load(content)
            elif file.endswith(".json"):
                content = json.loads(content)
            return True, content, "File loaded successfully"
        except Exception as e:
            return False, None, f"Failed to load file {file} from cache: {e}"

    def cache_get(self, key):
        """
        Get a value from the cache.

        :param key: The key to retrieve.
        :return: A tuple containing a success indicator, the loaded content, and a message.
        """
        file = None
        for cache_dir in self.cache_dirs:
            cache_path = os.path.join(cache_dir, key)
            if os.path.exists(cache_path):
                file = cache_path
                break
        if not file:
            return False, None, f"Cache entry not found: {key}"
        return self.load_file(file)

    def save_file(self, file, content):
        """
        Save a file to the cache.

        :param file: The file to save.
        :param content: The content to save.
        :return: A tuple containing a success indicator, the saved content, and a message.
        """
        try:
            if file.endswith(".yaml"):
                content = yaml.dump(content, default_flow_style=False)
            elif file.endswith(".json"):
                content = json.dumps(content, indent=4)
            with open(file, "w") as f:
                f.write(content)
            return True, content, f"File {file} saved successfully to cache"
        except Exception as e:
            return False, None, f"Failed to save file {file} to cache: {e}"

    def cache_set(self, key, value, cache_dir=None):
        """
        Set a value in the cache.

        :param key: The key to set.
        :param value: The value to set.
        :param cache_dir: The cache directory to use. If not provided, the first cache directory is used.
        :return: A tuple containing a success indicator, the value, and a message.
        """
        cache_dir = cache_dir or self.cache_dirs[0]
        if not os.path.exists(cache_dir):
            return False, None, f"Cache directory not found: {cache_dir}"
        cache_path = os.path.join(cache_dir, key)
        return self.save_file(cache_path, value)

    def cache_delete(self, key, cache_dir=None):
        """
        Delete a value from the cache.

        :param key: The key to delete.
        :param cache_dir: The cache directory to use. If not provided, the first cache directory is used.
        :return: A tuple containing a success indicator, the deleted content, and a message.
        """
        cache_dir = cache_dir or self.cache_dirs[0]
        if not os.path.exists(cache_dir):
            return False, None, f"Cache directory not found: {cache_dir}"
        cache_path = os.path.join(cache_dir, key)
        if os.path.exists(cache_path):
            os.remove(cache_path)
            return True, None, f"Cache entry {key} deleted successfully"
        return False, None, f"Cache entry not found: {key}"
