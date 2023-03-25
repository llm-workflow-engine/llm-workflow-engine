from sqlalchemy.exc import SQLAlchemyError

from chatgpt_wrapper.backends.openai.orm import Manager, Message
from chatgpt_wrapper.backends.openai.conversation import ConversationManager

class MessageManager(Manager):
    def __init__(self, config=None):
        super().__init__(config)
        self.conversation_manager = ConversationManager(self.config)

    def get_message(self, message_id):
        try:
            message = self.orm.session.query(Message).get(message_id)
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
            messages = self.orm.get_messages(conversation, limit=limit, offset=offset, target_id=None)
        except SQLAlchemyError as e:
            return self._handle_error(f"Failed to retrieve messages: {str(e)}")
        return True, messages, "Messages retrieved successfully"

    def add_message(self, conversation_id, role, message):
        success, conversation, user_message = self.conversation_manager.get_conversation(conversation_id)
        if not success:
            return success, conversation, user_message
        if not conversation:
            return False, None, "Conversation not found"
        try:
            message = self.orm.add_message(conversation, role, message)
        except SQLAlchemyError as e:
            return self._handle_error(f"Failed to add message: {str(e)}")
        return True, message, "Message added successfully"

    def edit_message(self, message_id, **kwargs):
        success, message, user_message = self.get_message(message_id)
        if not success:
            return success, message, user_message
        if not message:
            return False, None, "Message not found"
        try:
            updated_message = self.orm.edit_message(message, **kwargs)
        except SQLAlchemyError as e:
            return self._handle_error(f"Failed to edit message: {str(e)}")
        return True, updated_message, "Message edited successfully"

    def delete_message(self, message_id):
        success, message, user_message = self.get_message(message_id)
        if not success:
            return success, message, user_message
        if not message:
            return False, None, "Message not found"
        try:
            self.orm.delete_message(message)
        except SQLAlchemyError as e:
            return self._handle_error(f"Failed to delete message: {str(e)}")
        return True, None, "Message deleted successfully"
