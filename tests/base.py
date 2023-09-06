import os
import tempfile

from langchain.schema.messages import (
    # SystemMessage,
    # HumanMessage,
    AIMessage,
    # FunctionMessage,
    # AIMessageChunk,
)

from lwe.core.backend import Backend
from lwe.backends.api.request import ApiRequest

TEST_DIR = os.path.join(tempfile.gettempdir(), 'lwe_test')
TEST_CONFIG_DIR = os.path.join(TEST_DIR, 'config')
TEST_DATA_DIR = os.path.join(TEST_DIR, 'data')
TEST_PROFILE = 'test'

TEST_BASIC_MESSAGES = [
    {
        "message": "You are a helpful assistant.",
        "message_metadata": None,
        "message_type": "content",
        "role": "system",
    },
    {
        "message": "say hello",
        "message_metadata": None,
        "message_type": "content",
        "role": "user",
    },
    {
        "message": 'hello',
        "message_metadata": None,
        "message_type": "content",
        "role": "assistant",
    },
]

TEST_FUNCTION_CALL_RESPONSE_MESSAGES = [
    {
        "message": "You are a helpful assistant.",
        "message_metadata": None,
        "message_type": "content",
        "role": "system",
    },
    {
        "message": "repeat this word twice: foo",
        "message_metadata": None,
        "message_type": "content",
        "role": "user",
    },
    {
        "message": {
            "arguments": {"repeats": 2, "word": "foo"},
            "name": "test_function",
        },
        "message_metadata": None,
        "message_type": "function_call",
        "role": "assistant",
    },
    {
        "message": {"message": "Repeated the word foo 2 times.", "result": "foo foo"},
        "message_metadata": {"name": "test_function"},
        "message_type": "function_response",
        "role": "function",
    },
    {
        "message": 'The word "foo" repeated twice is: "foo foo".',
        "message_metadata": None,
        "message_type": "content",
        "role": "assistant",
    },
]


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


def fake_llm_responses(responses, request_overrides=None):
    request_overrides = request_overrides or {}
    request_overrides.setdefault('preset_overrides', {})
    request_overrides['preset_overrides'].setdefault('model_customizations', {})
    responses = [AIMessage(content=message) if isinstance(message, str) else message for message in responses]
    request_overrides['preset_overrides']['model_customizations']['responses'] = responses
    return request_overrides


def make_provider(provider_manager, provider_name='provider_fake_llm'):
    success, provider, user_message = provider_manager.load_provider(provider_name)
    if not success:
        raise Exception(user_message)
    provider.setup()
    return provider


def make_api_request(test_config,
                     function_manager,
                     provider_manager,
                     preset_manager,
                     provider=None,
                     input='test',
                     preset=None,
                     system_message=None,
                     old_messages=None,
                     max_submission_tokens=None,
                     request_overrides=None,
                     return_only=False,
                     ):
    provider = provider or make_provider(provider_manager)
    request = ApiRequest(config=test_config,
                         provider=provider,
                         provider_manager=provider_manager,
                         function_manager=function_manager,
                         input=input,
                         preset=preset,
                         preset_manager=preset_manager,
                         system_message=system_message,
                         old_messages=old_messages,
                         max_submission_tokens=max_submission_tokens,
                         request_overrides=request_overrides,
                         return_only=return_only,
                         )
    return request
