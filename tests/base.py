import os
import tempfile

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


def make_provider(provider_manager, provider_name='provider_fake_llm'):
    success, provider, user_message = provider_manager.load_provider(provider_name)
    if not success:
        raise Exception(user_message)
    provider.setup()
    return provider
