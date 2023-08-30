import os
import tempfile
import pytest

from lwe.core.config import Config
import lwe.core.util as util
from lwe.core.backend import Backend

TEST_DIR = os.path.join(tempfile.gettempdir(), 'lwe_test')
TEST_CONFIG_DIR = os.path.join(TEST_DIR, 'config')
TEST_DATA_DIR = os.path.join(TEST_DIR, 'data')
TEST_PROFILE = 'test'


@pytest.fixture
def test_config():
    util.remove_and_create_dir(TEST_CONFIG_DIR)
    util.remove_and_create_dir(TEST_DATA_DIR)
    config = Config(TEST_CONFIG_DIR, TEST_DATA_DIR, profile=TEST_PROFILE)
    return config


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
