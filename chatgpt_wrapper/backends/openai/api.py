import os
import threading
import openai
import tiktoken

from openai.error import OpenAIError

from langchain.chat_models.openai import ChatOpenAI, _convert_dict_to_message

from chatgpt_wrapper.core.backend import Backend
import chatgpt_wrapper.core.constants as constants
import chatgpt_wrapper.core.util as util
from chatgpt_wrapper.backends.openai.user import UserManager
from chatgpt_wrapper.backends.openai.conversation import ConversationManager
from chatgpt_wrapper.backends.openai.message import MessageManager

class OpenAIAPI(Backend):
    def __init__(self, config=None, default_user_id=None):
        super().__init__(config)
        self._configure_access_info()
        self.user_manager = UserManager(self.config)
        self.conversation = ConversationManager(self.config)
        self.message = MessageManager(self.config)
        self.current_user = None
        self.conversation_tokens = 0
        self.set_llm_class(ChatOpenAI)
        self.set_model_system_message()
        self.set_model_temperature(self.config.get('chat.model_customizations.temperature'))
        self.set_model_top_p(self.config.get('chat.model_customizations.top_p'))
        self.set_model_presence_penalty(self.config.get('chat.model_customizations.presence_penalty'))
        self.set_model_frequency_penalty(self.config.get('chat.model_customizations.frequency_penalty'))
        self.set_model_max_submission_tokens(self.config.get('chat.model_customizations.max_submission_tokens'))
        if default_user_id is not None:
            success, user, user_message = self.user_manager.get_by_user_id(default_user_id)
            if not success:
                raise Exception(user_message)
            self.set_current_user(user)

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
        if model not in self.available_models.values():
            raise NotImplementedError("Unsupported engine {self.engine}")
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            raise Exception(f"Unable to get token encoding for model {model}: {str(e)}")
        return encoding

    def get_num_tokens_from_messages(self, messages, encoding=None):
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
        tokens = self.get_conversation_token_count(conversation_id)
        self.conversation_tokens = tokens

    def get_conversation_token_count(self, conversation_id=None):
        conversation_id = conversation_id or self.conversation_id
        success, old_messages, user_message = self.message.get_messages(conversation_id)
        if not success:
            raise Exception(user_message)
        token_messages = self.prepare_prompt_messsage_context(old_messages)
        tokens = self.get_num_tokens_from_messages(token_messages)
        return tokens

    def extract_system_message(self, model_customizations):
        system_message = None
        if 'system_message' in model_customizations:
            system_message = model_customizations['system_message']
            del model_customizations['system_message']
            aliases = self.get_system_message_aliases()
            if system_message in aliases:
                system_message = aliases[system_message]
        return system_message, model_customizations

    def _extract_message_content(self, message):
        return message.content

    def gen_title_thread(self, conversation):
        self.log.info(f"Generating title for conversation {conversation.id}")
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
            success, completion, user_message = self._call_openai_non_streaming(new_messages, temperature=0)
            if success:
                title = self._extract_message_content(completion)
                self.log.info(f"Title generated for conversation {conversation.id}: {title}")
                success, conversation, user_message = self.conversation.edit_conversation_title(conversation.id, title)
                if success:
                    self.log.debug(f"Title saved for conversation {conversation.id}")
                    return
        self.log.info(f"Failed to generate title for conversation: {str(user_message)}")

    def gen_title(self, conversation):
        thread = threading.Thread(target=self.gen_title_thread, args=(conversation,))
        thread.start()

    def get_backend_name(self):
        return "chatgpt-api"

    def set_available_models(self):
        self.available_models = constants.OPENAPI_CHAT_RENDER_MODELS

    def set_model_system_message(self, message=constants.SYSTEM_MESSAGE_DEFAULT):
        self.model_system_message = message

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
  * Max submission tokens: %s
  * System message: %s
""" % (self.model, self.model_temperature, self.model_top_p, self.model_presence_penalty, self.model_frequency_penalty, self.model_max_submission_tokens, self.model_system_message)
        return output

    def get_system_message_aliases(self):
        aliases = self.config.get('chat.model_customizations.system_message')
        aliases['default'] = constants.SYSTEM_MESSAGE_DEFAULT
        return aliases

    def build_openai_message(self, role, content):
        message = {
            "role": role,
            "content": content,
        }
        return message

    def prepare_prompt_conversation_messages(self, prompt, conversation_id=None, target_id=None, system_message=None):
        old_messages = []
        new_messages = []
        if conversation_id:
            success, old_messages, message = self.message.get_messages(conversation_id, target_id=target_id)
            if not success:
                raise Exception(message)
        if len(old_messages) == 0:
            system_message = system_message or self.model_system_message
            new_messages.append(self.build_openai_message('system', system_message))
        new_messages.append(self.build_openai_message('user', prompt))
        return old_messages, new_messages

    def prepare_prompt_messsage_context(self, old_messages=[], new_messages=[]):
        messages = [self.build_openai_message(m.role, m.message) for m in old_messages]
        messages.extend(new_messages)
        return messages

    def create_new_conversation_if_needed(self, conversation_id=None, title=None):
        conversation_id = conversation_id or self.conversation_id
        if conversation_id:
            success, conversation, message = self.conversation.get_conversation(conversation_id)
            if not success:
                raise Exception(message)
        else:
            success, conversation, message = self.conversation.add_conversation(self.current_user.id, title=title, model=self.model)
            if not success:
                raise Exception(message)
        self.conversation_id = conversation.id
        return conversation

    def add_new_messages_to_conversation(self, conversation_id, new_messages, response_message, title=None):
        conversation = self.create_new_conversation_if_needed(conversation_id, title)
        for m in new_messages:
            success, message, user_message = self.message.add_message(conversation.id, m['role'], m['content'])
            if not success:
                raise Exception(user_message)
        success, last_message, user_message = self.message.add_message(conversation.id, 'assistant', response_message)
        if not success:
            raise Exception(user_message)
        tokens = self.get_conversation_token_count()
        self.conversation_tokens = tokens
        return conversation, last_message

    def add_message(self, role, message, conversation_id=None):
        conversation_id = conversation_id or self.conversation_id
        success, message, user_message = self.message.add_message(conversation_id, role, message)
        if not success:
            raise Exception(user_message)
        return message

    def _build_openai_chat_request(self, messages, temperature=None, top_p=None, presence_penalty=None, frequency_penalty=None, stream=False):
        temperature = self.model_temperature if temperature is None else temperature
        top_p = self.model_top_p if top_p is None else top_p
        presence_penalty = self.model_presence_penalty if presence_penalty is None else presence_penalty
        frequency_penalty = self.model_frequency_penalty if frequency_penalty is None else frequency_penalty
        self.log.debug(f"ChatCompletion.create with message count: {len(messages)}, model: {self.model}, temperature: {temperature}, top_p: {top_p}, presence_penalty: {presence_penalty}, frequency_penalty: {frequency_penalty}, stream: {stream})")
        args = {
            'model_name': self.model,
            'temperature': temperature,
            'top_p': top_p,
            'presence_penalty': presence_penalty,
            'frequency_penalty': frequency_penalty,
        }
        if stream:
            args.update(self.streaming_args(interrupt_handler=True))
        llm = self.make_llm(args)
        messages = [_convert_dict_to_message(m) for m in messages]
        return llm, messages

    def _call_openai_streaming(self, messages, temperature=None, top_p=None, presence_penalty=None, frequency_penalty=None):
        self.log.debug(f"Initiated streaming request with message count: {len(messages)}")
        llm, messages = self._build_openai_chat_request(messages, temperature=temperature, top_p=top_p, presence_penalty=presence_penalty, frequency_penalty=frequency_penalty, stream=True)
        try:
            response = llm(messages)
        except ValueError as e:
            return False, messages, e
        return True, response, "Response received"

    def _call_openai_non_streaming(self, messages, temperature=None, top_p=None, presence_penalty=None, frequency_penalty=None):
        self.log.debug(f"Initiated non-streaming request with message count: {len(messages)}")
        llm, messages = self._build_openai_chat_request(messages, temperature=temperature, top_p=top_p, presence_penalty=presence_penalty, frequency_penalty=frequency_penalty)
        try:
            response = llm(messages)
        except ValueError as e:
            return False, messages, e
        return True, response, "Response received"

    def set_current_user(self, user=None):
        self.current_user = user
        if self.current_user:
            self.set_active_model(self.current_user.default_model)
        else:
            self.set_active_model()

    def conversation_data_to_messages(self, conversation_data):
        return conversation_data['messages']

    def delete_conversation(self, conversation_id=None):
        conversation_id = conversation_id if conversation_id else self.conversation_id
        success, conversation, message = self.conversation.delete_conversation(conversation_id)
        return self._handle_response(success, conversation, message)

    def set_title(self, title, conversation_id=None):
        conversation_id = conversation_id if conversation_id else self.conversation_id
        success, conversation, user_message = self.conversation.edit_conversation_title(conversation_id, title)
        return self._handle_response(success, conversation, user_message)

    def get_history(self, limit=20, offset=0, user_id=None):
        user_id = user_id if user_id else self.current_user.id
        success, conversations, message = self.conversation.get_conversations(user_id, limit=limit, offset=offset)
        if success:
            history = {m.id: self.conversation.orm.object_as_dict(m) for m in conversations}
            return success, history, message
        return self._handle_response(success, conversations, message)

    def get_conversation(self, id=None):
        id = id if id else self.conversation_id
        success, conversation, message = self.conversation.get_conversation(id)
        if success:
            success, messages, message = self.message.get_messages(id)
            if success:
                conversation_data = {
                    "conversation": self.conversation.orm.object_as_dict(conversation),
                    "messages": [self.conversation.orm.object_as_dict(m) for m in messages],
                }
                return success, conversation_data, message
        return self._handle_response(success, conversation, message)

    def new_conversation(self):
        super().new_conversation()
        self.conversation_tokens = 0

    def _strip_out_messages_over_max_tokens(self, messages, token_count, max_tokens):
        stripped_messages_count = 0
        while token_count > max_tokens and len(messages) > 1:
            message = messages.pop(0)
            token_count = self.get_num_tokens_from_messages(messages)
            self.log.debug(f"Stripping message: {message['role']}, {message['content']} -- new token count: {token_count}")
            stripped_messages_count += 1
        token_count = self.get_num_tokens_from_messages(messages)
        if token_count > max_tokens:
            raise Exception(f"No messages to send, all messages have been stripped, still over max submission tokens: {max_tokens}")
        if stripped_messages_count > 0:
            max_tokens_exceeded_warning = f"Conversation exceeded max submission tokens ({max_tokens}), stripped out {stripped_messages_count} oldest messages before sending, sent {token_count} tokens instead"
            self.log.warning(max_tokens_exceeded_warning)
            util.print_status_message(False, max_tokens_exceeded_warning)
        return messages

    def _prepare_ask_request(self, prompt, system_message=None):
        old_messages, new_messages = self.prepare_prompt_conversation_messages(prompt, self.conversation_id, self.parent_message_id, system_message=system_message)
        messages = self.prepare_prompt_messsage_context(old_messages, new_messages)
        tokens = self.get_num_tokens_from_messages(messages)
        self.conversation_tokens = tokens
        messages = self._strip_out_messages_over_max_tokens(messages, self.conversation_tokens, self.model_max_submission_tokens)
        return new_messages, messages

    def _ask_request_post(self, conversation_id, new_messages, response_message, title=None):
        conversation_id = conversation_id or self.conversation_id
        if response_message:
            if self.current_user:
                conversation, last_message = self.add_new_messages_to_conversation(conversation_id, new_messages, response_message, title)
                self.parent_message_id = last_message.id
                if conversation.title:
                    self.log.debug(f"Conversation {conversation.id} already has title: {conversation.title}")
                else:
                    self.gen_title(conversation)
                return True, conversation, "Conversation updated with new messages"
            else:
                return True, response_message, "No current user, conversation not saved"
        return False, None, "Conversation not updated with new messages"

    def ask_stream(self, prompt, title=None, model_customizations={}):
        system_message, model_customizations = self.extract_system_message(model_customizations)
        new_messages, messages = self._prepare_ask_request(prompt, system_message=system_message)
        # Streaming loop.
        self.streaming = True
        #    if not self.streaming:
        #        self.log.info("Request to interrupt streaming")
        #        break
        self.log.debug(f"Started streaming response at {util.current_datetime().isoformat()}")
        success, response_obj, user_message = self._call_openai_streaming(messages, **model_customizations)
        if success:
            self.log.debug(f"Stopped streaming response at {util.current_datetime().isoformat()}")
            response_message = self._extract_message_content(response_obj)
            self.message_clipboard = response_message
            if not self.streaming:
                util.print_status_message(False, "Generation stopped")
            success, response_obj, user_message = self._ask_request_post(self.conversation_id, new_messages, response_message, title)
            if success:
                response_obj = response_message
        # End streaming loop.
        self.streaming = False
        return self._handle_response(success, response_obj, user_message)

    def ask(self, prompt, title=None, model_customizations={}):
        """
        Send a message to chatGPT and return the response.

        Args:
            message (str): The message to send.

        Returns:
            str: The response received from OpenAI.
        """
        system_message, model_customizations = self.extract_system_message(model_customizations)
        new_messages, messages = self._prepare_ask_request(prompt, system_message=system_message)
        success, response, user_message = self._call_openai_non_streaming(messages, **model_customizations)
        if success:
            response_message = self._extract_message_content(response)
            self.message_clipboard = response_message
            success, conversation, user_message = self._ask_request_post(self.conversation_id, new_messages, response_message, title)
            if success:
                return self._handle_response(success, response_message, user_message)
            return self._handle_response(success, conversation, user_message)
        return self._handle_response(success, response, user_message)
