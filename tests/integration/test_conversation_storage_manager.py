import copy

from lwe.backends.api.database import Database
from lwe.backends.api.orm import Orm, Manager
from lwe.backends.api.conversation_storage_manager import ConversationStorageManager

from ..base import (
    TEST_BASIC_MESSAGES,
    TEST_TOOL_CALL_RESPONSE_MESSAGES,
)


def make_conversation_storage_manager(
    test_config,
    tool_manager,
    provider_manager,
    current_user=False,
    conversation_id=None,
    preset_name=None,
):
    orm = Orm(test_config)
    database = Database(test_config, orm=orm)
    database.create_schema()
    if current_user is False:
        manager = Manager(test_config, orm=orm)
        current_user = manager.orm_add_user("test", None, None)
    return ConversationStorageManager(
        config=test_config,
        tool_manager=tool_manager,
        current_user=current_user,
        conversation_id=conversation_id,
        provider=provider_manager.get_provider_from_name("fake_llm"),
        preset_name=preset_name,
        provider_manager=provider_manager,
        orm=orm,
    )


def test_store_conversation_messages_new_messages_with_current_user(
    test_config, tool_manager, provider_manager
):
    csm = make_conversation_storage_manager(test_config, tool_manager, provider_manager)
    new_messages = copy.deepcopy(TEST_BASIC_MESSAGES)
    success, conversation, message = csm.store_conversation_messages(new_messages)
    assert success
    assert conversation is not None
    assert message == "Conversation updated with new messages"
    success, stored_conversation, user_message = csm.conversation.get_conversation(conversation.id)
    assert stored_conversation is not None
    success, stored_messages, user_message = csm.message.get_messages(conversation.id)
    assert len(stored_messages) == len(new_messages)


def test_store_conversation_messages_new_messages_with_tool_call_with_current_user(
    test_config, tool_manager, provider_manager
):
    csm = make_conversation_storage_manager(test_config, tool_manager, provider_manager)
    new_messages = copy.deepcopy(TEST_TOOL_CALL_RESPONSE_MESSAGES)
    success, conversation, message = csm.store_conversation_messages(new_messages)
    assert success
    assert conversation is not None
    assert message == "Conversation updated with new messages"
    success, stored_conversation, user_message = csm.conversation.get_conversation(conversation.id)
    assert stored_conversation is not None
    success, stored_messages, user_message = csm.message.get_messages(conversation.id)
    assert len(stored_messages) == len(new_messages)


def test_store_conversation_messages_existing_messages_with_current_user(
    test_config, tool_manager, provider_manager
):
    csm = make_conversation_storage_manager(test_config, tool_manager, provider_manager)
    new_messages = copy.deepcopy(TEST_BASIC_MESSAGES)
    success, conversation, message = csm.store_conversation_messages(new_messages)
    assert success
    # Bit of a hack, but preserves the in memory database.
    csm.conversation_id = conversation.id
    new_messages_2 = copy.deepcopy(TEST_BASIC_MESSAGES)
    new_messages_2.pop(0)
    success, updated_conversation, message = csm.store_conversation_messages(new_messages_2)
    assert updated_conversation.id == conversation.id
    success, stored_messages, _user_message = csm.message.get_messages(updated_conversation.id)
    assert len(stored_messages) == len(new_messages + new_messages_2)


def test_store_conversation_messages_without_current_user(
    test_config, tool_manager, provider_manager
):
    csm = make_conversation_storage_manager(
        test_config, tool_manager, provider_manager, current_user=None
    )
    new_messages = copy.deepcopy(TEST_BASIC_MESSAGES)
    success, response_content, message = csm.store_conversation_messages(new_messages, "test")
    assert success
    assert response_content == "test"
    assert message == "No current user, conversation not saved"


def test_get_conversation_token_count(test_config, tool_manager, provider_manager):
    csm = make_conversation_storage_manager(test_config, tool_manager, provider_manager)
    new_messages = copy.deepcopy(TEST_BASIC_MESSAGES)
    success, conversation, message = csm.store_conversation_messages(new_messages)
    assert success
    tokens = csm.get_conversation_token_count()
    assert tokens > 10


def test_gen_title_with_in_memory_sqlite(test_config, tool_manager, provider_manager):
    csm = make_conversation_storage_manager(test_config, tool_manager, provider_manager)
    new_messages = copy.deepcopy(TEST_BASIC_MESSAGES)
    success, conversation, message = csm.store_conversation_messages(new_messages)
    assert success
    assert conversation is not None
    success, stored_conversation, user_message = csm.conversation.get_conversation(conversation.id)
    assert stored_conversation is not None
    assert stored_conversation.title is not None
