#!/usr/bin/env python

import os
import sys
import openai

import chatgpt_wrapper.constants as constants
from chatgpt_wrapper.config import Config
from chatgpt_wrapper.logger import Logger
from chatgpt_wrapper.openai.orm import Orm
import chatgpt_wrapper.debug as debug
if False:
    debug.console(None)

class OpenAIAPI:
    def __init__(self, config=None):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self._configure_access_info()
        self.model = config.get('chat.model')
        self.orm = Orm(self.config)
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

    async def delete_conversation(self, uuid=None):
        raise NotImplementedError()
        if self.session is None:
            await self.refresh_session()
        if not uuid and not self.conversation_id:
            return
        id = uuid if uuid else self.conversation_id
        url = f"https://chat.openai.com/backend-api/conversation/{id}"
        data = {
            "is_visible": False,
        }
        ok, json, response = await self._api_patch_request(url, data)
        if ok:
            return json
        else:
            self.log.error("Failed to delete conversation")

    async def set_title(self, title, conversation_id=None):
        raise NotImplementedError()
        if self.session is None:
            await self.refresh_session()
        id = conversation_id if conversation_id else self.conversation_id
        url = f"https://chat.openai.com/backend-api/conversation/{id}"
        data = {
            "title": title,
        }
        ok, json, response = await self._api_patch_request(url, data)
        if ok:
            return json
        else:
            self.log.error("Failed to set title")

    async def get_history(self, limit=20, offset=0):
        # TODO: Logic for failed get?
        ok = True
        conversations = self.orm.get_conversations(self.current_user, limit=limit, offset=offset)
        debug.console(conversations[0].created_time)
        if ok:
            history = {m.id: vars(m) for m in conversations}
            return history
        else:
            self.log.error("Failed to get history")

    async def get_conversation(self, uuid=None):
        raise NotImplementedError()
        if self.session is None:
            await self.refresh_session()
        uuid = uuid if uuid else self.conversation_id
        if uuid:
            url = f"https://chat.openai.com/backend-api/conversation/{uuid}"
            ok, json, response = await self._api_get_request(url)
            if ok:
                return json
            else:
                self.log.error(f"Failed to get conversation {uuid}")

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

    def new_conversation(self):
        self.parent_message_id = None  # TODO: this needs to be fixed
        self.conversation_id = None
        self.conversation_title_set = None


def collect_args():
    args = " ".join(sys.argv[1:])
    return args

if __name__ == "__main__":
    collected_args = collect_args()
    api = OpenAIAPI()
    response = api.chat(collected_args)
    api.log.info(response.strip())
