import os
import pytest

from lwe.core.config import Config
from lwe.core.function_manager import FunctionManager
from lwe.core.function_cache import FunctionCache
from lwe.core.plugin_manager import PluginManager
from lwe.core.provider_manager import ProviderManager
from lwe.core.template_manager import TemplateManager
from lwe.core.preset_manager import PresetManager
import lwe.core.util as util
from .base import TEST_CONFIG_DIR, TEST_DATA_DIR, TEST_PROFILE
from .base import FakeBackend


def set_environment_variables():
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "fake-api-key")


@pytest.fixture
def test_config():
    util.remove_and_create_dir(TEST_CONFIG_DIR)
    util.remove_and_create_dir(TEST_DATA_DIR)
    set_environment_variables()
    config = Config(TEST_CONFIG_DIR, TEST_DATA_DIR, profile=TEST_PROFILE)
    config.set("backend_options.auto_create_first_user", "test")
    config.set("backend_options.title_generation.provider", "fake_llm")
    config.set("database", "sqlite:///:memory:")
    config.set("model.default_preset", "test")
    config.set("plugins.enabled", ["provider_fake_llm"])
    return config


@pytest.fixture
def function_manager(test_config):
    additional_functions = {
        "test_function2": "test_function2_path",
        "test_function3": "test_function3_path",
    }
    function_manager = FunctionManager(
        config=test_config, additional_functions=additional_functions
    )
    return function_manager


@pytest.fixture
def function_cache(test_config, function_manager):
    function_cache = FunctionCache(
        test_config,
        function_manager,
    )
    return function_cache


@pytest.fixture
def plugin_manager(test_config, function_manager):
    backend = FakeBackend(test_config)
    plugin_manager = PluginManager(test_config, backend)
    return plugin_manager


@pytest.fixture
def provider_manager(test_config, plugin_manager):
    provider_manager = ProviderManager(test_config, plugin_manager)
    return provider_manager


@pytest.fixture
def template_manager(test_config):
    template_manager = TemplateManager(config=test_config)
    template_manager.load_templates()
    return template_manager


@pytest.fixture
def preset_manager(test_config):
    preset_manager = PresetManager(test_config)
    return preset_manager
