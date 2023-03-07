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
        self.set_system_message()

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

    def set_system_message(self, message=constants.SYSTEM_MESSAGE_DEFAULT):
        self.system_message = message

    def build_openai_message(self, role, content):
        message = {
            "role": role,
            "content": content,
        }
        return message

    def prepare_prompt_conversation_messages(self, prompt, conversation_id=None, target_id=None):
        old_messages = []
        new_messages = []
        if conversation_id:
            success, old_messages, message = self.message.get_messages(conversation_id, target_id=target_id)
            if not success:
                raise Exception(message)
        if len(old_messages) == 0:
            new_messages.append(self.build_openai_message('system', self.system_message))
        new_messages.append(self.build_openai_message('user', prompt))
        return old_messages, new_messages

    def prepare_prompt_messsage_context(self, old_messages=[], new_messages=[]):
        self.create_new_converation_if_needed()
        messages = [self.build_openai_message(m.role, m.message) for m in old_messages]
        messages.extend(new_messages)
        return messages

    def create_new_converation_if_needed(self):
        if not self.conversation_id:
            success, conversation, message = self.conversation.create_conversation(self.current_user.id, model=self.model)
            if success:
                self.conversation_id = conversation.id
                return conversation
            else:
                raise Exception(message)

    def add_new_messages_to_conversation(self, conversation_id, new_messages, response_message):
        for m in new_messages:
            success, message, user_message = self.message.add_message(conversation_id, m['role'], m['content'])
            if not success:
                raise Exception(user_message)
        success, last_message, user_message = self.message.add_message(conversation_id, 'assistant', response_message)
        if success:
            return last_message
        else:
            raise Exception(user_message)

    def add_message(self, role, message, conversation_id=None):
        conversation_id = conversation_id or self.conversation_id
        success, message, user_message = self.message.add_message(conversation_id, role, message)
        if success:
            return message
        else:
            raise Exception(user_message)

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
        old_messages, new_messages = self.prepare_prompt_conversation_messages(prompt, self.conversation_id, self.parent_message_id)
        messages = self.prepare_prompt_messsage_context(old_messages, new_messages)
        debug.console(old_messages)
        debug.console(new_messages)
        debug.console(messages)
        response_message = ""
        # Streaming loop.
        self.streaming = True
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
        if response_message:
            last_message = self.add_new_messages_to_conversation(self.conversation_id, new_messages, response_message)
            self.parent_message_id = last_message.id
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
        old_messages, new_messages = self.prepare_prompt_conversation_messages(prompt, self.conversation_id, self.parent_message_id)
        messages = self.prepare_prompt_messsage_context(old_messages, new_messages)
        success, response_message, message = await self._call_openai_non_streaming(messages)
        if success:
            last_message = self.add_new_messages_to_conversation(self.conversation_id, new_messages, response_message)
            self.parent_message_id = last_message.id
        return self._handle_response(success, response_message, message)
