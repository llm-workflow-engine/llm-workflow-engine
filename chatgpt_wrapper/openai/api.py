import os
import asyncio
import threading
import openai
import tiktoken

from chatgpt_wrapper.backend import Backend
from chatgpt_wrapper.config import Config
from chatgpt_wrapper.logger import Logger
import chatgpt_wrapper.constants as constants
from chatgpt_wrapper.openai.conversation import ConversationManager
from chatgpt_wrapper.openai.message import MessageManager
import chatgpt_wrapper.debug as debug
if False:
    debug.console(None)

class AsyncOpenAIAPI(Backend):
    def __init__(self, config=None):
        super().__init__(config)
        self._configure_access_info()
        self.conversation = ConversationManager(self.config)
        self.message = MessageManager(self.config)
        self.current_user = None
        self.conversation_tokens = 0
        self.set_system_message()
        self.set_model_temperature(self.config.get('chat.model_customizations.temperature'))
        self.set_model_top_p(self.config.get('chat.model_customizations.top_p'))
        self.set_model_presence_penalty(self.config.get('chat.model_customizations.presence_penalty'))
        self.set_model_frequency_penalty(self.config.get('chat.model_customizations.frequency_penalty'))
        self.set_model_max_submission_tokens(self.config.get('chat.model_customizations.max_submission_tokens'))

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

    def get_token_encoding(self, model="gpt-3.5-turbo"):
        if model not in constants.OPENAPI_CHAT_RENDER_MODELS.values():
            raise NotImplementedError("Unsupported engine {self.engine}")
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            raise Exception(f"Unable to get token encoding for model {model}: {str(e)}")
        return encoding

    def num_tokens_from_messages(self, messages, encoding=None):
        if not encoding:
            encoding = self.get_token_encoding()
        """Returns the number of tokens used by a list of messages."""
        num_tokens = 0
        for message in messages:
            num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
            for key, value in message.items():
                num_tokens += len(encoding.encode(value))
                if key == "name":  # if there's a name, the role is omitted
                    num_tokens += -1  # role is always required and always 1 token
        num_tokens += 2  # every reply is primed with <im_start>assistant
        return num_tokens

    def switch_to_conversation(self, conversation_id, parent_message_id):
        super().switch_to_conversation(conversation_id, parent_message_id)
        tokens = self.conversation_token_count(conversation_id)
        self.conversation_tokens = tokens

    def conversation_token_count(self, conversation_id=None):
        conversation_id = conversation_id or self.conversation_id
        success, old_messages, user_message = self.message.get_messages(conversation_id)
        if not success:
            raise Exception(user_message)
        token_messages = self.prepare_prompt_messsage_context(old_messages)
        tokens = self.num_tokens_from_messages(token_messages)
        return tokens

    def _extract_completion_content(self, completion):
        content = "".join([c.message.content for c in completion.choices])
        return content

    async def gen_title_thread_async(self, conversation):
        if conversation.title:
            self.log.debug(f"Conversation {conversation.id} already has title: {conversation.title}")
        else:
            self.log.info(f"Generating title for {conversation.title}")
            # NOTE: This might need to be smarter in the future, but for now
            # it should be reasonable to assume that the second record is the
            # first user message we need for generating the title.
            success, messages, user_message = self.message.get_messages(conversation.id, limit=2)
            if success:
                user_content = messages[1].message
                new_messages = [
                    self.build_openai_message('system', constants.DEFAULT_TITLE_GENERATION_SYSTEM_PROMPT),
                    self.build_openai_message('user', "%s: %s" % (constants.DEFAULT_TITLE_GENERATION_USER_PROMPT, user_content)),
                ]
                success, completion, user_message = await self._call_openai_non_streaming(new_messages, temperature=0)
                if success:
                    title = self._extract_completion_content(completion)
                    self.log.info(f"Title generated for conversation {conversation.id}: {title}")
                    success, conversation, user_message = self.conversation.edit_conversation_title(conversation.id, title)
                    if success:
                        self.log.debug(f"Title saved for conversation {conversation.id}")
                        return
            self.log.info(f"Failed to generate title for conversation: {str(user_message)}")

    def gen_title_thread(self, conversation):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.gen_title_thread_async(conversation))

    def gen_title(self, conversation):
        thread = threading.Thread(target=self.gen_title_thread, args=(conversation,))
        thread.start()

    def set_system_message(self, message=constants.SYSTEM_MESSAGE_DEFAULT):
        self.system_message = message

    def set_model_temperature(self, temperature=constants.OPENAPI_DEFAULT_TEMPERATURE):
        self.model_temperature = temperature

    def set_model_top_p(self, top_p=constants.OPENAPI_DEFAULT_TOP_P):
        self.model_top_p = top_p

    def set_model_presence_penalty(self, presence_penalty=constants.OPENAPI_DEFAULT_PRESENCE_PENALTY):
        self.model_presence_penalty = presence_penalty

    def set_model_frequency_penalty(self, frequency_penalty=constants.OPENAPI_DEFAULT_FREQUENCY_PENALTY):
        self.model_frequency_penalty = frequency_penalty

    def set_model_max_submission_tokens(self, max_submission_tokens=constants.OPENAPI_DEFAULT_MAX_SUBMISSION_TOKENS):
        self.model_max_submission_tokens = max_submission_tokens

    def get_runtime_config(self):
        output = """
* Model customizations:
  * Model: %s
  * Temperature: %s
  * top_p: %s
  * Presence penalty: %s
  * Frequency penalty: %s
""" % (self.model, self.model_temperature, self.model_top_p, self.model_presence_penalty, self.model_frequency_penalty)
        return output

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
        messages = [self.build_openai_message(m.role, m.message) for m in old_messages]
        messages.extend(new_messages)
        return messages

    def create_new_converation_if_needed(self, conversation_id=None):
        conversation_id = conversation_id or self.conversation_id
        if conversation_id:
            success, conversation, message = self.conversation.get_conversation(conversation_id)
            if not success:
                raise Exception(message)
        else:
            success, conversation, message = self.conversation.add_conversation(self.current_user.id, model=self.model)
            if not success:
                raise Exception(message)
        self.conversation_id = conversation.id
        return conversation

    def add_new_messages_to_conversation(self, conversation_id, new_messages, response_message):
        conversation = self.create_new_converation_if_needed(conversation_id)
        for m in new_messages:
            success, message, user_message = self.message.add_message(conversation.id, m['role'], m['content'])
            if not success:
                raise Exception(user_message)
        success, last_message, user_message = self.message.add_message(conversation.id, 'assistant', response_message)
        if success:
            tokens = self.conversation_token_count()
            self.conversation_tokens = tokens
        else:
            raise Exception(user_message)
        return conversation, last_message

    def add_message(self, role, message, conversation_id=None):
        conversation_id = conversation_id or self.conversation_id
        success, message, user_message = self.message.add_message(conversation_id, role, message)
        if success:
            return message
        else:
            raise Exception(user_message)

    async def _build_openai_chat_request(self, messages, temperature=None, top_p=None, presence_penalty=None, frequency_penalty=None, stream=False):
        temperature = self.model_temperature if temperature is None else temperature
        top_p = self.model_top_p if top_p is None else top_p
        presence_penalty = self.model_presence_penalty if presence_penalty is None else presence_penalty
        frequency_penalty = self.model_frequency_penalty if frequency_penalty is None else frequency_penalty
        response = await openai.ChatCompletion.acreate(
            model=self.model,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            stream=stream,
        )
        self.log.debug(f"ChatCompletion.create with message count: {len(messages)}, model: {self.model}, temperature: {temperature}, top_p: {top_p}, presence_penalty: {presence_penalty}, frequency_penalty: {frequency_penalty}, stream: {stream})")
        return response

    async def _call_openai_streaming(self, messages, temperature=None, top_p=None, presence_penalty=None, frequency_penalty=None):
        self.log.debug(f"Initiated streaming request with message count: {len(messages)}")
        response = await self._build_openai_chat_request(messages, temperature=temperature, top_p=top_p, presence_penalty=presence_penalty, frequency_penalty=frequency_penalty, stream=True)
        async for chunk in response:
            yield chunk

    async def _call_openai_non_streaming(self, messages, temperature=None, top_p=None, presence_penalty=None, frequency_penalty=None):
        self.log.debug(f"Initiated non-streaming request with message count: {len(messages)}")
        completion = await self._build_openai_chat_request(messages, temperature=temperature, top_p=top_p, presence_penalty=presence_penalty, frequency_penalty=frequency_penalty)
        return True, completion, "Retrieved response"

    def set_current_user(self, user=None):
        self.current_user = user
        if user:
            self.model = constants.OPENAPI_CHAT_RENDER_MODELS[self.current_user.default_model]
        else:
            self.model = None

    def conversation_data_to_messages(self, conversation_data):
        return conversation_data['messages']

    async def delete_conversation(self, conversation_id=None):
        conversation_id = conversation_id if conversation_id else self.conversation_id
        success, conversation, message = self.conversation.delete_conversation(conversation_id)
        return self._handle_response(success, conversation, message)

    async def set_title(self, title, conversation=None):
        conversation = conversation if conversation else self.conversation.get_conversation(self.conversation_id)
        success, conversation, message = self.conversation.edit_conversation_title(conversation, title)
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

    def new_conversation(self):
        super().new_conversation()
        self.conversation_tokens = 0

    def _prepare_ask_request(self, prompt):
        old_messages, new_messages = self.prepare_prompt_conversation_messages(prompt, self.conversation_id, self.parent_message_id)
        messages = self.prepare_prompt_messsage_context(old_messages, new_messages)
        tokens = self.num_tokens_from_messages(messages)
        self.conversation_tokens = tokens
        return new_messages, messages

    def _ask_request_post(self, conversation_id, new_messages, response_message):
        conversation_id = conversation_id or self.conversation_id
        if response_message:
            if self.current_user:
                conversation, last_message = self.add_new_messages_to_conversation(conversation_id, new_messages, response_message)
                self.parent_message_id = last_message.id
                self.gen_title(conversation)
                return True, conversation, "Conversation updated with new messages"
            else:
                return True, response_message, "No current user, conversation not saved"
        return False, None, "Conversation not updated with new messages"

    async def ask_stream(self, prompt):
        new_messages, messages = self._prepare_ask_request(prompt)
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
        if not self.streaming:
            yield (
                "\nGeneration stopped\n"
            )
        # End streaming loop.
        self.streaming = False
        self._ask_request_post(self.conversation_id, new_messages, response_message)

    async def ask(self, prompt):
        """
        Send a message to chatGPT and return the response.

        Args:
            message (str): The message to send.

        Returns:
            str: The response received from OpenAI.
        """
        new_messages, messages = self._prepare_ask_request(prompt)
        success, completion, message = await self._call_openai_non_streaming(messages)
        if success:
            response_message = self._extract_completion_content(completion)
            success, conversation, message = self._ask_request_post(self.conversation_id, new_messages, response_message)
            if success:
                return self._handle_response(success, response_message, message)
            return self._handle_response(success, conversation, message)
        return self._handle_response(success, completion, message)

class OpenAIAPI:
    def __init__(self, config=None):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.async_openai_api = AsyncOpenAIAPI(config)
        self.async_run(self.async_openai_api.create(timeout, proxy))

    def __getattr__(self, __name: str):
        if hasattr(self.async_openai_api, __name):
            return getattr(self.async_openai_api, __name)
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{__name}'")

    def async_run(self, awaitable):
        return asyncio.get_event_loop().run_until_complete(awaitable)

    def ask_stream(self, prompt: str):
        def iter_over_async(ait):
            loop = asyncio.get_event_loop()
            ait = ait.__aiter__()
            async def get_next():
                try:
                    obj = await ait.__anext__()
                    return False, obj
                except StopAsyncIteration:
                    return True, None
            while True:
                done, obj = loop.run_until_complete(get_next())
                if done:
                    break
                yield obj
        yield from iter_over_async(self.async_openai_api.ask_stream(prompt))

    def ask(self, message: str) -> str:
        return self.async_run(self.async_openai_api.ask(message))

    def get_conversation(self, id=None):
        return self.async_run(self.async_openai_api.get_conversation(id))

    def delete_conversation(self, id=None):
        return self.async_run(self.async_openai_api.delete_conversation(id))

    def set_title(self, title, conversation_id=None):
        return self.async_run(self.async_openai_api.set_title(title, conversation_id))

    def get_history(self, limit=20, offset=0):
        return self.async_run(self.async_openai_api.get_history(limit, offset))
