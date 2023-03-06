#!/usr/bin/env python

import os
import sys
import openai

import chatgpt_wrapper.constants as constants
from chatgpt_wrapper.config import Config
from chatgpt_wrapper.logger import Logger
from chatgpt_wrapper.openai.conversation import ConversationManagement
from chatgpt_wrapper.openai.message import MessageManagement
import chatgpt_wrapper.debug as debug
if False:
    debug.console(None)

class OpenAIAPI:
    def __init__(self, config=None):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self._configure_access_info()
        self.model = config.get('chat.model')
        self.conversation = ConversationManagement(self.config)
        self.message = MessageManagement(self.config)
        self.current_user = None
        # TODO: These two attributes need to be integrated into the backend
        # for shell compat.
        self.parent_message_id = None
        self.conversation_id = None

    def _configure_access_info(self):
        self.openai = openai
        profile_prefix = f"PROFILE_{self.config.profile.upper()}"
        self.openai.organization = os.getenv(f"{profile_prefix}_OPENAI_ORG_ID")
        if not self.openai.organization:
            self.openai.organization = os.getenv("OPENAI_ORG_ID")
        self.openai.api_key = os.getenv(f"{profile_prefix}_OPENAI_API_KEY")
        if not self.openai.api_key:
            self.openai.api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai.api_key:
            raise ValueError(f"{profile_prefix}_OPENAI_API_KEY or OPENAI_API_KEY environment variable must be set")

    async def _gen_title(self):
        raise NotImplementedError()
        if not self.conversation_id or self.conversation_id and self.conversation_title_set:
            return
        url = f"https://chat.openai.com/backend-api/conversation/gen_title/{self.conversation_id}"
        data = {
            "message_id": self.parent_message_id,
            "model": constants.API_RENDER_MODELS[self.model],
        }
        ok, json, response = await self._api_post_request(url, data)
        if ok:
            # TODO: Do we want to do anything with the title we got back?
            # response_data = response.json()
            self.conversation_title_set = True
        else:
            self.log.warning("Failed to auto-generate title for new conversation")

    def set_current_user(self, user=None):
        self.current_user = user
        self.model = constants.API_RENDER_MODELS[self.current_user.default_model]

    def conversation_data_to_messages(self, conversation_data):
        return conversation_data['messages']

    async def delete_conversation(self, conversation_id=None):
        conversation_id = conversation_id if conversation_id else self.conversation_id
        success, conversation, message = self.conversation.delete_conversation(conversation_id)
        return success, conversation, message

    async def set_title(self, title, conversation=None):
        conversation = conversation if conversation else self.conversation.get_conversation(self.conversation_id)
        success, conversation, message = self.conversation.update_conversation_title(conversation, title)
        return success, conversation, message

    async def get_history(self, limit=20, offset=0):
        success, conversations, message = self.conversation.get_conversations(self.current_user, limit=limit, offset=offset)
        if success:
            history = {m.id: vars(m) for m in conversations}
            return success, history, message
        else:
            return success, conversations, message

    async def get_conversation(self, id=None):
        id = id if id else self.conversation_id
        success, conversation, message = self.conversation.get_conversation(id)
        if success:
            success, messages, message = self.message.get_messages(id)
            if success:
                conversation_data = {
                    "conversation": vars(conversation),
                    "messages": [vars(m) for m in messages],
                }
                return success, conversation_data, message
            else:
                return success, conversation, message
        else:
            return success, conversation, message

    async def ask_stream(self, prompt: str):
        raise NotImplementedError()
        new_message_id = str(uuid.uuid4())

        request = {
            "messages": [
                {
                    "id": new_message_id,
                    "role": "user",
                    "content": {"content_type": "text", "parts": [prompt]},
                }
            ],
            "model": constants.API_RENDER_MODELS[self.model],
            "conversation_id": self.conversation_id,
            "parent_message_id": self.parent_message_id,
            "action": "next",
        }
        self.streaming = True
        if not self.streaming:
            yield (
                "\nGeneration stopped\n"
            )
        self.streaming = False
        await self._gen_title()

    def terminate_stream(self, _signal, _frame):
        self.log.info("Received signal to terminate stream")
        if self.streaming:
            self.streaming = False

    async def ask(self, message: str) -> str:
        """
        Send a message to chatGPT and return the response.

        Args:
            message (str): The message to send.

        Returns:
            str: The response received from OpenAI.
        """
        messages = [
            {
                "role": "user",
                "content": message,
            },
        ]
        completion = self.openai.ChatCompletion.create(model=self.model, messages=messages)
        response = completion.choices[0].message.content
        return response
        raise NotImplementedError()

    async def new_conversation(self):
        self.parent_message_id = None  # TODO: this needs to be fixed
        self.conversation_id = None
        self.conversation_title_set = None
