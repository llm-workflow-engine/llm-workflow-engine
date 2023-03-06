from sqlalchemy.exc import SQLAlchemyError

from chatgpt_wrapper.config import Config
from chatgpt_wrapper.logger import Logger
from chatgpt_wrapper.openai.orm import Orm, Conversation, Message
import chatgpt_wrapper.debug as debug
if False:
    debug.console(None)

class MessageManagement:
    def __init__(self, config=None):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.orm = Orm(self.config)

    def get_message(self, message_id):
        message = self.orm.session.query(Message).get(message_id)
        if not message:
            return (False, None, "Message not found")
        return (True, message, "Message retrieved successfully")

    def get_messages(self, conversation_id, limit=None, offset=None):
        conversation = self.orm.session.query(Conversation).get(conversation_id)
        if not conversation:
            return (False, None, "Conversation not found")
        try:
            messages = self.orm.get_messages(conversation, limit=limit, offset=offset)
            return (True, messages, "Messages retrieved successfully")
        except Exception as e:
            self.log.error(f"Failed to retrieve messages: {e}")
            return (False, None, "Failed to retrieve messages")

    def add_message(self, conversation_id, role, message):
        conversation = self.orm.session.query(Conversation).get(conversation_id)
        if not conversation:
            return (False, None, "Conversation not found")
        try:
            message = self.orm.add_message(conversation, role, message)
            return (True, message, "Message added successfully")
        except SQLAlchemyError as e:
            self.log.error(f"Failed to add message: {e}")
            return (False, None, "Failed to add message")

    def edit_message(self, message_id, **kwargs):
        message = self.orm.session.query(Message).get(message_id)
        if not message:
            return (False, None, "Message not found")
        try:
            updated_message = self.orm.edit_message(message, **kwargs)
            return (True, updated_message, "Message edited successfully")
        except SQLAlchemyError as e:
            self.log.error(f"Failed to edit message: {e}")
            return (False, None, "Failed to edit message")

    def delete_message(self, message_id):
        message = self.orm.session.query(Message).get(message_id)
        if not message:
            return (False, None, "Message not found")
        try:
            self.orm.delete_message(message)
            return (True, None, "Message deleted successfully")
        except SQLAlchemyError as e:
            self.log.error(f"Failed to delete message: {e}")
            return (False, None, "Failed to delete message")

