import os
import openai

from chatgpt_wrapper.backend import Backend
import chatgpt_wrapper.constants as constants
from chatgpt_wrapper.openai.conversation import ConversationManagement
from chatgpt_wrapper.openai.message import MessageManagement
import chatgpt_wrapper.debug as debug
if False:
    debug.console(None)

class OpenAIAPI(Backend):
    def __init__(self, config=None):
        super().__init__(config)
        self._configure_access_info()
        self.conversation = ConversationManagement(self.config)
        self.message = MessageManagement(self.config)
        self.current_user = None

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

    def _handle_response(self, success, obj, message):
        if not success:
            self.log.error(message)
        return success, obj, message

    async def _gen_title(self, prompt):
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

    def _build_openai_message_list(self, prompt, conversation_id=None):
        # TODO: Include sytem prompt and older messages, token counting, etc.
        messages = [
            {
                "role": "user",
                "content": prompt,
            },
        ]
        return messages

    async def _build_openai_chat_request(self, messages, temperature=0, stream=False):
        response = await openai.ChatCompletion.acreate(
            model=self.model,
            messages=messages,
            temperature=temperature,
            stream=stream,
        )
        return response

    async def _call_openai_streaming(self, messages, temperature=0):
        response = await self._build_openai_chat_request(messages, temperature, stream=True)
        async for chunk in response:
            yield chunk

    async def _call_openai_non_streaming(self, messages, temperature=0):
        completion = await self._build_openai_chat_request(messages, temperature)
        response = completion.choices[0].message.content
        return True, response, "Retrieved stuff"

    def set_current_user(self, user=None):
        self.current_user = user
        self.model = constants.API_RENDER_MODELS[self.current_user.default_model]

    def conversation_data_to_messages(self, conversation_data):
        return conversation_data['messages']

    async def delete_conversation(self, conversation_id=None):
        conversation_id = conversation_id if conversation_id else self.conversation_id
        success, conversation, message = self.conversation.delete_conversation(conversation_id)
        return self._handle_response(success, conversation, message)

    async def set_title(self, title, conversation=None):
        conversation = conversation if conversation else self.conversation.get_conversation(self.conversation_id)
        success, conversation, message = self.conversation.update_conversation_title(conversation, title)
        return self._handle_response(success, conversation, message)

    async def get_history(self, limit=20, offset=0):
        success, conversations, message = self.conversation.get_conversations(self.current_user.id, limit=limit, offset=offset)
        if success:
            history = {m.id: vars(m) for m in conversations}
            return success, history, message
        return self._handle_response(success, conversations, message)

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
        return self._handle_response(success, conversation, message)

    async def ask_stream(self, prompt: str):
        if not self.conversation_id:
            success, conversation, message = self.conversation.create_conversation(self.current_user.id, model=self.model)
            if success:
                self.conversation_id = conversation.id
            else:
                raise Exception(message)
        success, message, user_message = self.message.add_message(self.conversation_id, 'user', prompt)
        if success:
            self.parent_message_id = message.id
        else:
            raise Exception(message)
        # Streaming loop.
        self.streaming = True
        messages = self._build_openai_message_list(prompt)
        response_message = ""
        async for response in self._call_openai_streaming(messages):
            if not self.streaming:
                self.log.info("Request to interrupt streaming")
                break
            if 'choices' in response:
                for choice in response['choices']:
                    delta = choice['delta']
                    if 'role' in delta and delta['role'] == 'assistant':
                        self.log.debug(f"Started streaming response at {response['created']}")
                    elif len(delta) == 0:
                        self.log.debug(f"Stopped streaming response at {response['created']}, cause: {response['choices'][0]['finish_reason']}")
                    elif 'content' in delta:
                        response_message += delta['content']
                        yield delta['content']
        if response_message and self.current_user:
            success, message, user_message = self.message.add_message(self.conversation_id, 'assistant', response_message)
            if success:
                self.parent_message_id = message.id
            else:
                raise Exception(message)
        if not self.streaming:
            yield (
                "\nGeneration stopped\n"
            )
        # End streaming loop.
        self.streaming = False
        # TODO: Implement.
        # await self._gen_title(prompt)

    async def ask(self, prompt: str) -> str:
        """
        Send a message to chatGPT and return the response.

        Args:
            message (str): The message to send.

        Returns:
            str: The response received from OpenAI.
        """
        messages = self._build_openai_message_list(prompt)
        success, response, message = await self._call_openai_non_streaming(messages)
        return self._handle_response(success, response, message)
