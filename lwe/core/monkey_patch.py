import logging
import langchain.callbacks.manager
import langchain.chat_models.openai
from langchain.chat_models.openai import _convert_dict_to_message

from typing import (
    Any,
    List,
    Optional,
)
from langchain.callbacks.base import (
    BaseCallbackHandler,
)
from langchain.schema import (
    get_buffer_string,
)

from langchain.callbacks.manager import (
    CallbackManagerForLLMRun,
)
from langchain.schema import (
    BaseMessage,
    ChatGeneration,
    ChatResult,
)

logger = logging.getLogger(__name__)

class StreamInterruption(Exception):
    """Exception to signal an interruption to a streaming response."""
    pass

def _handle_event(
    handlers: List[BaseCallbackHandler],
    event_name: str,
    ignore_condition_name: Optional[str],
    *args: Any,
    **kwargs: Any,
) -> None:
    """Generic event handler for CallbackManager."""
    message_strings: Optional[List[str]] = None
    for handler in handlers:
        try:
            if ignore_condition_name is None or not getattr(
                handler, ignore_condition_name
            ):
                getattr(handler, event_name)(*args, **kwargs)
        except StreamInterruption as e:
            raise StreamInterruption(e)
        except NotImplementedError as e:
            if event_name == "on_chat_model_start":
                if message_strings is None:
                    message_strings = [get_buffer_string(m) for m in args[1]]
                _handle_event(
                    [handler],
                    "on_llm_start",
                    "ignore_llm",
                    args[0],
                    message_strings,
                    *args[2:],
                    **kwargs,
                )
            else:
                logger.warning(f"Error in {event_name} callback: {e}")
        except Exception as e:
            if handler.raise_error:
                raise e
            logger.warning(f"Error in {event_name} callback: {e}")
langchain.callbacks.manager._handle_event = _handle_event
langchain.callbacks.manager.StreamInterruption = StreamInterruption

def _generate(
    self,
    messages: List[BaseMessage],
    stop: Optional[List[str]] = None,
    run_manager: Optional[CallbackManagerForLLMRun] = None,
    **kwargs: Any,
) -> ChatResult:
    message_dicts, params = self._create_message_dicts(messages, stop)
    params = {**params, **kwargs}
    if self.streaming:
        inner_completion = ""
        role = "assistant"
        params["stream"] = True
        function_call: Optional[dict] = None
        response = self.completion_with_retry(messages=message_dicts, **params)
        try:
            for stream_resp in response:
                role = stream_resp["choices"][0]["delta"].get("role", role)
                token = stream_resp["choices"][0]["delta"].get("content") or ""
                inner_completion += token
                _function_call = stream_resp["choices"][0]["delta"].get("function_call")
                if _function_call:
                    if function_call is None:
                        function_call = _function_call
                    else:
                        function_call["arguments"] += _function_call["arguments"]
                if run_manager:
                    run_manager.on_llm_new_token(token)
        except StreamInterruption as e:
            logger.warning(e)
        finally:
            response.close()
        message = _convert_dict_to_message(
            {
                "content": inner_completion,
                "role": role,
                "function_call": function_call,
            }
        )
        return ChatResult(generations=[ChatGeneration(message=message)])
    response = self.completion_with_retry(messages=message_dicts, **params)
    return self._create_chat_result(response)
langchain.chat_models.openai.ChatOpenAI._generate = _generate
