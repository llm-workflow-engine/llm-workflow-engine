from sqlalchemy.exc import SQLAlchemyError

from chatgpt_wrapper.config import Config
from chatgpt_wrapper.logger import Logger
from chatgpt_wrapper.openai.orm import Orm
import chatgpt_wrapper.debug as debug
if False:
    debug.console(None)

class ConversationManagement:
    def __init__(self, config=None):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.orm = Orm(self.config)

    def get_conversations(self, user, limit=None, offset=None, order_desc=True):
        try:
            conversations = self.orm.get_conversations(user, limit, offset, order_desc)
            return True, conversations, "Conversations retrieved successfully."
        except SQLAlchemyError as e:
            return False, None, f"Failed to retrieve conversations: {str(e)}"

    def create_conversation(self, user, title, model="default", hidden=False):
        try:
            conversation = self.orm.add_conversation(user, title, model, hidden)
            return True, conversation, "Conversation created successfully."
        except SQLAlchemyError as e:
            return False, None, f"Failed to create conversation: {str(e)}"

    def get_conversation(self, conversation_id):
        try:
            conversation = self.orm.get_conversation(conversation_id)
            if conversation:
                return True, conversation, "Conversation retrieved successfully."
            else:
                return False, None, "Conversation not found."
        except SQLAlchemyError as e:
            return False, None, f"Failed to retrieve conversation: {str(e)}"

    def update_conversation_title(self, conversation_id, new_title):
        try:
            success, conversation, message = self.get_conversation(conversation_id)
            updated_conversation = self.orm.edit_conversation(conversation, title=new_title)
            return True, updated_conversation, "Conversation title updated successfully."
        except SQLAlchemyError as e:
            return False, None, f"Failed to update conversation title: {str(e)}"

    def hide_conversation(self, conversation_id):
        try:
            success, conversation, message = self.get_conversation(conversation_id)
            updated_conversation = self.orm.edit_conversation(conversation, hidden=True)
            return True, updated_conversation, "Conversation hidden successfully."
        except SQLAlchemyError as e:
            return False, None, f"Failed to hide conversation: {str(e)}"

    def unhide_conversation(self, conversation_id):
        try:
            success, conversation, message = self.get_conversation(conversation_id)
            updated_conversation = self.orm.edit_conversation(conversation, hidden=False)
            return True, updated_conversation, "Conversation unhidden successfully."
        except SQLAlchemyError as e:
            return False, None, f"Failed to unhide conversation: {str(e)}"

    def delete_conversation(self, conversation_id):
        try:
            success, conversation, message = self.get_conversation(conversation_id)
            self.orm.delete_conversation(conversation)
            return True, None, "Conversation deleted successfully."
        except SQLAlchemyError as e:
            return False, None, f"Failed to delete conversation: {str(e)}"
