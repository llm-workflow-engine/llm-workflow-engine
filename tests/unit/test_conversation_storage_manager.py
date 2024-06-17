from unittest.mock import Mock

from lwe.core import constants
from lwe.backends.api.conversation_storage_manager import ConversationStorageManager


def make_conversation_storage_manager(
    test_config,
    tool_manager,
    provider_manager,
    current_user=None,
    conversation_id=None,
    preset_name=None,
):
    return ConversationStorageManager(
        config=test_config,
        tool_manager=tool_manager,
        current_user=current_user,
        conversation_id=conversation_id,
        provider=provider_manager.get_provider_from_name("fake_llm"),
        model_name=constants.API_BACKEND_DEFAULT_MODEL,
        preset_name=preset_name,
        provider_manager=provider_manager,
        orm=Mock(),
    )


def test_init(test_config, tool_manager, provider_manager):
    csm = make_conversation_storage_manager(test_config, tool_manager, provider_manager)
    assert csm.config == test_config
    assert csm.tool_manager == tool_manager
    assert csm.provider_manager == provider_manager


def test_store_conversation_messages_no_current_user(test_config, tool_manager, provider_manager):
    csm = make_conversation_storage_manager(test_config, tool_manager, provider_manager)
    success, response_content, message = csm.store_conversation_messages([], "response_content")
    assert success
    assert response_content == "response_content"
    assert message == "No current user, conversation not saved"


def test_store_conversation_messages_with_current_user_no_title(
    test_config, tool_manager, provider_manager
):
    csm = make_conversation_storage_manager(
        test_config, tool_manager, provider_manager, current_user=Mock()
    )
    conversation_mock = Mock()
    conversation_mock.title = None
    csm.add_new_messages_to_conversation = Mock(
        return_value=(True, (conversation_mock, Mock()), "Success")
    )
    csm.gen_title = Mock()
    success, conversation, message = csm.store_conversation_messages([], "response_content")
    assert success
    assert conversation == conversation_mock
    assert message == "Conversation updated with new messages"
    assert csm.add_new_messages_to_conversation.call_count == 1
    assert csm.gen_title.call_count == 1


def test_store_conversation_messages_with_current_user_with_title(
    test_config, tool_manager, provider_manager
):
    csm = make_conversation_storage_manager(
        test_config, tool_manager, provider_manager, current_user=Mock()
    )
    conversation_mock = Mock()
    conversation_mock.title = "title"
    csm.add_new_messages_to_conversation = Mock(
        return_value=(True, (conversation_mock, Mock()), "Success")
    )
    csm.gen_title = Mock()
    success, conversation, message = csm.store_conversation_messages([], "response_content")
    assert success
    assert conversation == conversation_mock
    assert message == "Conversation updated with new messages"
    assert csm.add_new_messages_to_conversation.call_count == 1
    assert csm.gen_title.call_count == 0


def test_create_new_conversation_if_needed_existing_conversation(
    test_config, tool_manager, provider_manager
):
    csm = make_conversation_storage_manager(
        test_config, tool_manager, provider_manager, current_user=Mock(), conversation_id=1
    )
    conversation_mock = Mock()
    csm.conversation.get_conversation = Mock(return_value=(True, conversation_mock, "Success"))
    conversation = csm.create_new_conversation_if_needed()
    assert conversation == conversation_mock
    assert csm.conversation.get_conversation.call_count == 1


def test_create_new_conversation_if_needed_new_conversation(
    test_config, tool_manager, provider_manager
):
    csm = make_conversation_storage_manager(
        test_config, tool_manager, provider_manager, current_user=Mock()
    )
    conversation_mock = Mock()
    conversation_mock.id = 1
    csm.conversation.add_conversation = Mock(return_value=(True, conversation_mock, "Success"))
    conversation = csm.create_new_conversation_if_needed()
    assert conversation == conversation_mock
    assert csm.conversation.add_conversation.call_count == 1


def test_add_new_messages_to_conversation(test_config, tool_manager, provider_manager):
    csm = make_conversation_storage_manager(
        test_config, tool_manager, provider_manager, current_user=Mock()
    )
    message_mock = Mock()
    conversation_mock = Mock()
    conversation_mock.id = 1
    csm.message.add_message = Mock(return_value=(True, message_mock, "Success"))
    csm.conversation.add_conversation = Mock(return_value=(True, conversation_mock, "Success"))
    success, response, message = csm.add_new_messages_to_conversation(
        [{"role": "user", "message": "Hello", "message_type": "content", "message_metadata": None}],
        "Title",
    )
    assert success
    conversation, last_message = response
    assert conversation == conversation_mock
    assert last_message == message_mock
    assert csm.message.add_message.call_count == 1
    assert message.startswith("Added new messages to conversation")


def test_add_message(test_config, tool_manager, provider_manager):
    csm = make_conversation_storage_manager(
        test_config, tool_manager, provider_manager, current_user=Mock(), conversation_id=1
    )
    message_mock = Mock()
    success_message = "Message added successfully"
    csm.message.add_message = Mock(return_value=(True, message_mock, success_message))
    success, message, user_message = csm.add_message("user", "test", "content", None)
    assert success
    assert message == message_mock
    assert user_message == success_message
    assert csm.message.add_message.call_args.args[0] == 1
    assert csm.message.add_message.call_args.args[1] == "user"
    assert csm.message.add_message.call_args.args[2] == "test"
    assert csm.message.add_message.call_args.args[3] == "content"
    assert csm.message.add_message.call_args.args[4] is None
    assert csm.message.add_message.call_args.args[5] == "provider_fake_llm"
    assert csm.message.add_message.call_args.args[6] == constants.API_BACKEND_DEFAULT_MODEL
    assert csm.message.add_message.call_args.args[7] == ""


def test_get_conversation_token_count(test_config, tool_manager, provider_manager):
    csm = make_conversation_storage_manager(
        test_config, tool_manager, provider_manager, current_user=Mock(), conversation_id=1
    )
    messages = [
        {"role": "user", "message": "Hello", "message_type": "content", "message_metadata": None}
    ]
    csm.message.get_messages = Mock(return_value=(True, messages, "Success"))
    token_count = 100
    csm.token_manager.get_num_tokens_from_messages = Mock(return_value=token_count)
    tokens = csm.get_conversation_token_count()
    assert csm.token_manager.get_num_tokens_from_messages.call_args.args[0] == messages
    assert tokens == token_count
