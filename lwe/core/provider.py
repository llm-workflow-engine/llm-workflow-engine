from abc import abstractmethod
import copy

from typing import (
    Any,
    Mapping,
)

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from lwe.core.plugin import Plugin
from lwe.core import constants
from lwe.core import util


class PresetValue:
    def __init__(
        self,
        value_type,
        min_value=None,
        max_value=None,
        options=None,
        include_none=False,
        private=False,
    ):
        options = options or {}
        self.value_type = value_type
        self.min_value = min_value
        self.max_value = max_value
        self.options = options
        self.include_none = include_none
        self.private = private
        self.completions = {}
        self.build_completions()

    def build_completions(self):
        if self.value_type == bool:
            self.completions = {
                "true": None,
                "false": None,
            }
        elif self.value_type == int:
            if self.min_value is not None and self.max_value is not None:
                self.completions = util.list_to_completion_hash(
                    range(self.min_value, self.max_value + 1)
                )
        elif self.value_type == float:
            if self.min_value is not None and self.max_value is not None:
                self.completions = util.float_range_to_completions(self.min_value, self.max_value)
        elif self.value_type == str:
            self.completions = util.list_to_completion_hash(self.options)
        elif self.value_type == dict:
            pass
        else:
            raise ValueError(
                "Invalid value type provided. Must be one of the following: str, int, float, bool"
            )
        if self.value_type != dict and self.include_none:
            self.completions["None"] = None

    def cast(self, value):
        if value == "None" or value is None:
            return True, None, None
        if self.value_type == bool:
            if isinstance(value, bool):
                return True, value, None
            elif value.lower() in ["true", "t", "1"]:
                return True, True, None
            elif value.lower() in ["false", "f", "0"]:
                return True, False, None
            else:
                return (
                    False,
                    None,
                    "Invalid value provided. Must be one of the following: true, false",
                )
        elif self.value_type == int:
            try:
                return True, int(value), None
            except ValueError:
                return False, None, "Invalid value provided. Must be an integer"
        elif self.value_type == float:
            try:
                return True, float(value), None
            except ValueError:
                return False, None, "Invalid value provided. Must be a float"
        elif self.value_type == str:
            return True, str(value), None
        else:
            return (
                False,
                None,
                "Invalid value type provided. Must be one of the following: str, int, float, bool",
            )


class ProviderBase(Plugin):

    @property
    def display_name(self):
        return self.name[len(constants.PROVIDER_PREFIX) :]

    @property
    def plugin_type(self):
        return "provider"

    @property
    def model_property_name(self):
        return "model_name"

    @property
    def available_models(self):
        return self.get_capability("models", {}).keys()

    def setup(self):
        self.load_models()
        self.set_customizations(self.default_customizations())

    def default_config(self):
        return {}

    def load_models(self):
        self.models = self.config.get(f"plugins.{self.name}.models")
        if not self.models:
            if hasattr(self, "fetch_models"):
                try:
                    success, data, _user_message = self.cache_manager.cache_get(
                        self.plugin_cache_filename
                    )
                    if success:
                        self.models = data["models"]
                    else:
                        message = f"Fetching data for {self.name}\nData can be refreshed by running '{constants.COMMAND_LEADER}plugin reload {self.name}'"
                        self.log.info(message)
                        util.print_status_message(True, message)
                        self.models = self.fetch_models()
                        self.write_plugin_cache_file({"models": self.models})
                except Exception as e:
                    message = f"Could not fetch data for {self.name}: {e}"
                    self.log.error(message)
                    util.print_status_message(False, message)
                    self.models = copy.deepcopy(self.static_models)
            else:
                self.models = copy.deepcopy(self.static_models)

    @property
    def static_models(self):
        return {}

    def default_customizations(self, defaults=None):
        defaults = defaults or {}
        llm_class = self.llm_factory()
        llm = llm_class(**defaults)
        llm_defaults = llm.dict()
        custom_config = self.customization_config()
        defaults = {k: v for k, v in llm_defaults.items() if k in custom_config}
        if self.default_model:
            defaults[self.model_property_name] = self.default_model
        defaults["_type"] = llm_defaults["_type"]
        return defaults

    # NOTE: This is a best-guess approach for random dict values.
    def cast_dict_value(self, value):
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    pass
        return value

    def calculate_customization_value(self, orig_keys, new_value):
        if isinstance(orig_keys, str):
            orig_keys = orig_keys.split(".")
        keys = orig_keys.copy()
        config = self.customization_config()
        while keys:
            key = keys.pop(0)
            if key in config:
                config = config[key]
                if config is None:
                    return True, new_value, "Passing through value."
                elif config == dict:
                    return True, self.cast_dict_value(new_value), "Found dict key."
                # Special case: some LLM classes return an unset key for a nested config by default
                # so pass through this unset key.
                elif len(keys) == 0 and isinstance(config, dict):
                    return True, None, f"Returning None for unconfigured dict '{key}'."
                elif isinstance(config, PresetValue):
                    success, new_value, user_message = config.cast(new_value)
                    if success:
                        return True, new_value, "Found preset value."
                    return False, None, user_message
            else:
                break
        return False, None, f"Invalid key {key}."

    def get_customization_value(self, keys):
        if isinstance(keys, str):
            keys = keys.split(".")
        customizations = self.customizations.copy()
        while keys:
            key = keys.pop(0)
            if key in customizations:
                customizations = customizations[key]
                if not isinstance(customizations, dict):
                    return True, customizations, f"Found key {key}"
                # Special case: some LLM classes return an unset key for a nested config by default
                # so pass through this unset key.
                elif len(keys) == 0:
                    return True, None, f"Returning None for unconfigured dict '{key}'."
        return False, None, f"Invalid key {key}."

    def set_customization_value(self, keys, new_value):
        if isinstance(keys, str):
            keys = keys.split(".")
        if isinstance(new_value, dict):
            for k, v in new_value.items():
                success, new_value, user_message = self.set_customization_value(keys + [k], v)
                if not success:
                    return success, new_value, user_message
            return success, new_value, user_message
        else:
            success, new_value, user_message = self.calculate_customization_value(keys, new_value)
            if success:
                self.set_value(keys, new_value)
                return success, self.customizations, f"Set {'.'.join(keys)} to {new_value}"
            else:
                return success, new_value, user_message

    def set_value(self, keys, value):
        customizations = self.customizations
        for key in keys[:-1]:
            if customizations.get(key) is None:
                customizations[key] = {}
            customizations = customizations.setdefault(key, {})
        customizations[keys[-1]] = value

    def get_customizations(self, customizations=None):
        customizations = self.customizations if customizations is None else customizations
        # _type key exists in the Langchain output of dict(llm), and must be filtered out.
        customizations = {k: v for k, v in customizations.items() if k != "_type"}
        return customizations

    def set_customizations(self, customizations):
        self.customizations = customizations

    def customizations_to_completions(self):
        def dict_to_completions(completions, items, prefix=None, is_dict=False):
            prefix = prefix or []
            for key, value in items.items():
                full_key = ".".join(prefix + [key])
                if value is None:
                    continue
                elif value == dict:
                    completions[full_key] = {}
                elif isinstance(value, dict):
                    new_prefix = prefix + [key]
                    for k, v in value.items():
                        dict_key = "%s.%s" % (full_key, k)
                        if isinstance(v, PresetValue):
                            completions[dict_key] = v.completions
                        else:
                            completions[dict_key] = None
                    dict_to_completions(completions, value, new_prefix, is_dict)
                elif isinstance(value, PresetValue):
                    completions[full_key] = value.completions
                else:
                    completions[full_key] = value
            return completions

        completions = dict_to_completions({}, self.customization_config())
        return completions

    def get_capability(self, capability, default=False):
        if capability == "models":
            return self.models
        return self.capabilities[capability] if capability in self.capabilities else default

    def get_model(self):
        success, model_name, user_message = self.get_customization_value(self.model_property_name)
        if success:
            return model_name

    def set_model(self, model_name):
        models = self.get_capability("models", {})
        validate_models = self.get_capability("validate_models", True)
        if not validate_models or model_name in models:
            return self.set_customization_value(self.model_property_name, model_name)
        else:
            return False, None, f"Invalid model {model_name}"

    def transform_tools(self, tools):
        if hasattr(self, "transform_tool"):
            self.log.debug(f"Transforming tools for provider {self.display_name}")
            tools = [self.transform_tool(tool) for tool in tools]
        return tools

    def transform_openai_tool_spec_to_json_schema_spec(self, spec):
        json_schema_spec = {
            "description": spec["description"],
            "title": spec["name"],
            "properties": {},
        }
        for prop, details in spec["parameters"]["properties"].items():
            json_schema_spec["properties"][prop] = {
                "description": details["description"],
                "type": details["type"],
                "title": prop,
                "required": prop in spec["parameters"]["required"],
            }
        return json_schema_spec

    def make_llm(self, customizations=None, tools=None, tool_choice=None, use_defaults=False):
        customizations = customizations or {}
        final_customizations = (
            self.get_customizations(self.default_customizations())
            if use_defaults
            else self.get_customizations()
        )
        final_customizations.update(customizations)
        for key in constants.PROVIDER_PRIVATE_CUSTOMIZATION_KEYS:
            final_customizations.pop(key, None)
        llm_class = self.llm_factory()
        llm = llm_class(**final_customizations)
        if tools:
            self.log.debug(f"Provider {self.display_name} called with tools")
            kwargs = {
                "tools": self.transform_tools(tools),
            }
            if tool_choice:
                kwargs["tool_choice"] = tool_choice
            try:
                llm = llm.bind_tools(**kwargs)
            except NotImplementedError:
                self.log.warning(f"Provider {self.display_name} does not support tools")
        return llm

    def prepare_messages_method(self):
        return self.prepare_messages_for_llm_last_message

    def prepare_messages_for_llm_last_message(self, messages):
        messages = messages[-1]["content"]
        return messages

    def prepare_messages_for_llm_stuff_messages(self, messages):
        messages = [m["content"] for m in messages]
        return "\n\n".join(messages)

    def prepare_messages_for_llm_chat(self, messages):
        messages = [self.convert_dict_to_message(m) for m in messages]
        return messages

    def prepare_messages_for_llm(self, messages):
        method = self.prepare_messages_method()
        messages = method(messages)
        return messages

    def max_submission_tokens(self):
        models = self.get_capability("models", {})
        model_name = self.get_model()
        if model_name and model_name in models and "max_tokens" in models[model_name]:
            return models[model_name]["max_tokens"]
        return constants.OPEN_AI_DEFAULT_MAX_SUBMISSION_TOKENS

    def convert_ai_dict_to_message(self, message: Mapping[str, Any]) -> AIMessage:
        """Convert an LWE message dictionary to a LangChain AIMessage.

        This default implementation supports a format suitable for OpenAI.
        Other providers plugins may need to override this method depending
        on the structure of their AI messages.
        """
        content = message.get("content", "")
        kwargs = {}
        tool_calls = message.get("tool_calls", None)
        if tool_calls:
            kwargs["tool_calls"] = tool_calls
        # NOTE: Remove this if Langchain intetrations ever consistently
        # support using AIMessage.tool_calls property.
        additional_kwargs = message.get("additional_kwargs", None)
        if additional_kwargs:
            kwargs["additional_kwargs"] = additional_kwargs
        return AIMessage(content=content, **kwargs)

    def convert_dict_to_message(self, message: Mapping[str, Any]) -> BaseMessage:
        """Convert an LWE message dictionary to a LangChain message."""
        role = message.get("role")
        content = message.get("content", "")
        if role == "user":
            return HumanMessage(content=content)
        elif role == "assistant":
            return self.convert_ai_dict_to_message(message)
        elif role == "system":
            return SystemMessage(content=content)
        elif role == "tool":
            return ToolMessage(
                content=content,
                tool_call_id=message.get("tool_call_id"),
                name=message.get("name", None),
            )
        else:
            raise ValueError(f"Unknown role: {role}")

    def prepare_file_for_llm(self, file: dict):
        return file


class Provider(ProviderBase):
    @property
    @abstractmethod
    def capabilities(self):
        pass

    @property
    @abstractmethod
    def default_model(self):
        pass

    @abstractmethod
    def llm_factory(self):
        pass

    @abstractmethod
    def customization_config(self):
        pass
