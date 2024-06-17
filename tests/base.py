import re
import os
import tempfile

from langchain_core.messages import AIMessage

from lwe.core import constants
import lwe.core.util as util
from lwe.backends.api.backend import ApiBackend
from lwe.backends.api.request import ApiRequest

TEST_DIR = os.path.join(tempfile.gettempdir(), "lwe_test")
TEST_CONFIG_DIR = os.path.join(TEST_DIR, "config")
TEST_DATA_DIR = os.path.join(TEST_DIR, "data")
TEST_PROFILE = "test"

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
        "message": "hello",
        "message_metadata": None,
        "message_type": "content",
        "role": "assistant",
    },
]

TEST_TOOL_CALL_RESPONSE_MESSAGES = [
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
            "name": "test_tool",
        },
        "message_metadata": None,
        "message_type": "tool_call",
        "role": "assistant",
    },
    {
        "message": {"message": "Repeated the word foo 2 times.", "result": "foo foo"},
        "message_metadata": {"name": "test_tool"},
        "message_type": "tool_response",
        "role": "tool",
    },
    {
        "message": 'The word "foo" repeated twice is: "foo foo".',
        "message_metadata": None,
        "message_type": "content",
        "role": "assistant",
    },
]


class FakeBackend(ApiBackend):
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


def store_system_message(backend, conversation, message=constants.SYSTEM_MESSAGE_DEFAULT):
    backend.message.add_message(
        conversation.id,
        "system",
        message,
        "content",
        None,
        "provider_fake_llm",
        constants.API_BACKEND_DEFAULT_MODEL,
        "",
    )


def store_user_message(backend, conversation, message="test question"):
    success, message, user_message = backend.message.add_message(
        conversation.id,
        "user",
        message,
        "content",
        None,
        "provider_fake_llm",
        constants.API_BACKEND_DEFAULT_MODEL,
        "",
    )
    if success:
        return message
    raise Exception(user_message)


def store_assistant_message(backend, conversation, message="test response"):
    success, message, user_message = backend.message.add_message(
        conversation.id,
        "assistant",
        message,
        "content",
        None,
        "provider_fake_llm",
        constants.API_BACKEND_DEFAULT_MODEL,
        "",
    )
    if success:
        return message
    raise Exception(user_message)


def store_conversation(backend, title="Conversation"):
    success, conversation, user_message = backend.conversation.add_conversation(
        backend.current_user.id, title
    )
    if success:
        return conversation
    raise Exception(user_message)


def store_conversation_thread(backend, title="Conversation", rounds=1):
    conversation = store_conversation(backend, title)
    store_system_message(backend, conversation)
    for i in range(rounds):
        store_user_message(backend, conversation, f"test question {i}")
        store_assistant_message(backend, conversation, f"test response {i}")


def store_conversation_threads(backend, title="Conversation", rounds=3):
    for i in range(rounds):
        store_conversation_thread(backend, f"{title} {i}")


def clean_output(output):
    return re.sub(r"\x1b\[.*?m", "", output)


def fake_llm_responses(responses, request_overrides=None):
    request_overrides = request_overrides or {}
    request_overrides.setdefault("preset_overrides", {})
    request_overrides["preset_overrides"].setdefault("model_customizations", {})
    responses = [
        AIMessage(content=message) if isinstance(message, str) else message for message in responses
    ]
    request_overrides["preset_overrides"]["model_customizations"]["responses"] = responses
    return request_overrides


def make_template_file(template_manager, template_name, content=None):
    template_dir = template_manager.user_template_dirs[0]
    filepath = util.create_file(template_dir, template_name, content)
    template_manager.load_templates()
    return filepath


def make_provider(provider_manager, provider_name="provider_fake_llm"):
    success, provider, user_message = provider_manager.load_provider(provider_name)
    if not success:
        raise Exception(user_message)
    provider.setup()
    return provider


def make_api_request(
    test_config,
    tool_manager,
    provider_manager,
    preset_manager,
    provider=None,
    input="test",
    preset=None,
    system_message=None,
    old_messages=None,
    max_submission_tokens=None,
    request_overrides=None,
    return_only=False,
):
    provider = provider or make_provider(provider_manager)
    request = ApiRequest(
        config=test_config,
        provider=provider,
        provider_manager=provider_manager,
        tool_manager=tool_manager,
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
