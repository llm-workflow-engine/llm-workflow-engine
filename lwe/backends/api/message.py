import json

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import object_mapper

from lwe.backends.api.orm import Manager, Message
from lwe.backends.api.conversation import ConversationManager

JSON_MESSAGE_TYPES = ["tool_call", "tool_response"]


class MessageManager(Manager):
    def __init__(self, config=None, orm=None):
        super().__init__(config, orm)
        self.conversation_manager = ConversationManager(self.config, self.orm)

    def build_message(self, role, message, message_type="content", message_metadata=None):
        message = {
            "role": role,
            "message": message,
            "message_type": message_type,
            "message_metadata": message_metadata,
        }
        return message

    def message_to_storage(self, message, message_type, message_metadata):
        if message_type in JSON_MESSAGE_TYPES:
            message = json.dumps(message)
        message_metadata = json.dumps(message_metadata) if message_metadata else None
        return message, message_metadata

    def message_from_storage(self, message):
        if isinstance(message, Message):
            message = {c.key: getattr(message, c.key) for c in object_mapper(message).columns}
        if message["message_type"] in JSON_MESSAGE_TYPES:
            message["message"] = json.loads(message["message"], strict=False)
        message["message_metadata"] = (
            json.loads(message["message_metadata"]) if message["message_metadata"] else None
        )
        return message

    def get_message(self, message_id):
        try:
            message = self.session.query(Message).get(message_id)
            message = self.message_from_storage(message)
        except SQLAlchemyError as e:
            return self._handle_error(f"Failed to retrieve message: {str(e)}")
        if not message:
            return False, None, "Message not found"
        return True, message, "Message retrieved successfully"

    def get_messages(self, conversation_id, limit=None, offset=None, target_id=None):
        success, conversation, message = self.conversation_manager.get_conversation(conversation_id)
        if not success:
            return success, conversation, message
        if not conversation:
            return False, None, "Conversation not found"
        try:
            messages = self.orm_get_messages(
                conversation, limit=limit, offset=offset, target_id=None
            )
            messages = [self.message_from_storage(message) for message in messages]
        except SQLAlchemyError as e:
            return self._handle_error(f"Failed to retrieve messages: {str(e)}")
        return True, messages, "Messages retrieved successfully"

    def get_last_message(self, conversation_id):
        success, conversation, message = self.conversation_manager.get_conversation(conversation_id)
        if not success:
            return success, conversation, message
        if not conversation:
            return False, None, "Conversation not found"
        try:
            last_message = self.orm_get_last_message(conversation)
            last_message = self.message_from_storage(last_message)
        except SQLAlchemyError as e:
            return self._handle_error(f"Failed to retrieve last message: {str(e)}")
        return True, last_message, "Last message retrieved successfully"

    def add_message(
        self,
        conversation_id,
        role,
        message,
        message_type=None,
        message_metadata=None,
        provider=None,
        model=None,
        preset=None,
    ):
        success, conversation, user_message = self.conversation_manager.get_conversation(
            conversation_id
        )
        if not success:
            return success, conversation, user_message
        if not conversation:
            return False, None, "Conversation not found"
        try:
            message, message_metadata = self.message_to_storage(
                message, message_type, message_metadata
            )
            message = self.orm_add_message(
                conversation, role, message, message_type, message_metadata, provider, model, preset
            )
        except SQLAlchemyError as e:
            return self._handle_error(f"Failed to add message: {str(e)}")
        return True, message, "Message added successfully"

    # TODO: Currently unused, but would need to account for self.message_to_storage() if used.
    # def edit_message(self, message_id, **kwargs):
    #     success, message, user_message = self.get_message(message_id)
    #     if not success:
    #         return success, message, user_message
    #     if not message:
    #         return False, None, "Message not found"
    #     try:
    #         updated_message = self.orm_edit_message(message, **kwargs)
    #     except SQLAlchemyError as e:
    #         return self._handle_error(f"Failed to edit message: {str(e)}")
    #     return True, updated_message, "Message edited successfully"

    def delete_message(self, message_id):
        success, message, user_message = self.get_message(message_id)
        if not success:
            return success, message, user_message
        if not message:
            return False, None, "Message not found"
        try:
            self.orm_delete_message(message)
        except SQLAlchemyError as e:
            return self._handle_error(f"Failed to delete message: {str(e)}")
        return True, None, "Message deleted successfully"
