import os
import tempfile
import pytest

from lwe.core.config import Config
from lwe.core.function_manager import FunctionManager
from lwe.core.function_cache import FunctionCache
from lwe.core.plugin_manager import PluginManager
from lwe.core.provider_manager import ProviderManager
from lwe.core.template import TemplateManager
import lwe.core.util as util
from lwe.core.backend import Backend

TEST_DIR = os.path.join(tempfile.gettempdir(), 'lwe_test')
TEST_CONFIG_DIR = os.path.join(TEST_DIR, 'config')
TEST_DATA_DIR = os.path.join(TEST_DIR, 'data')
TEST_PROFILE = 'test'


class FakeBackend(Backend):
    name = "api"

    def conversation_data_to_messages(self, conversation_data):
        pass

    def delete_conversation(self, uuid=None):
        pass

    def set_title(self, title, conversation_id=None):
        pass

    def get_history(self, limit=20, offset=0):
        pass

    def get_conversation(self, uuid=None):
        pass

    def ask_stream(self, input: str, request_overrides: dict):
        pass

    def ask(self, input: str, request_overrides: dict):
        pass


@pytest.fixture
def test_config():
    util.remove_and_create_dir(TEST_CONFIG_DIR)
    util.remove_and_create_dir(TEST_DATA_DIR)
    config = Config(TEST_CONFIG_DIR, TEST_DATA_DIR, profile=TEST_PROFILE)
    return config


@pytest.fixture
def function_manager(test_config):
    function_manager = FunctionManager(config=test_config)
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
    plugin_manager = PluginManager(test_config, backend, additional_plugins=['provider_chat_openai', 'provider_fake_llm'])
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
