import os
import pytest

from lwe.core.config import Config
from lwe.core.tool_manager import ToolManager
from lwe.core.tool_cache import ToolCache
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
def tool_manager(test_config):
    additional_tools = {
        "test_tool2": "test_tool2_path",
        "test_tool3": "test_tool3_path",
    }
    tool_manager = ToolManager(config=test_config, additional_tools=additional_tools)
    return tool_manager


@pytest.fixture
def tool_cache(test_config, tool_manager):
    tool_cache = ToolCache(
        test_config,
        tool_manager,
    )
    return tool_cache


@pytest.fixture
def plugin_manager(test_config, tool_manager):
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
