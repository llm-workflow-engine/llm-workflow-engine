import copy

from abc import abstractmethod

from chatgpt_wrapper.core.plugin import Plugin
from chatgpt_wrapper.core import util

class PresetValue:
    def __init__(self, value_type, min_value=None, max_value=None, options={}, include_none=False, private=False):
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
                'true': None,
                'false': None,
            }
        elif self.value_type == int:
            if self.min_value is not None and self.max_value is not None:
                self.completions = util.list_to_completion_hash(range(self.min_value, self.max_value + 1))
        elif self.value_type == float:
            if self.min_value is not None and self.max_value is not None:
                self.completions = util.float_range_to_completions(self.min_value, self.max_value)
        elif self.value_type == str:
            self.completions = util.list_to_completion_hash(self.options)
        elif self.value_type == dict:
            pass
        else:
            raise ValueError("Invalid value type provided. Must be one of the following: str, int, float, bool")
        if self.value_type != dict and self.include_none:
            self.completions['None'] = None

    def cast(self, value):
        if value == 'None':
            return True, None, None
        if self.value_type == bool:
            if value.lower() in ['true', 't', '1']:
                return True, True, None
            elif value.lower() in ['false', 'f', '0']:
                return True, False, None
            else:
                return False, None, "Invalid value provided. Must be one of the following: true, false"
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
            return False, None, "Invalid value type provided. Must be one of the following: str, int, float, bool"

class ProviderBase(Plugin):

    def __init__(self, config=None):
        super().__init__(config)

    @property
    def plugin_type(self):
        return 'provider'

    def incompatible_backends(self):
        return [
            'chatgpt-browser',
        ]

    def setup(self):
        self.set_customizations(self.default_customizations())

    def default_config(self):
        return {}

    def default_customizations(self):
        llm_class = self.llm_factory()
        llm = llm_class()
        llm_defaults = llm.dict()
        custom_config = self.customization_config()
        # TODO: This feels hacky, but currently needed to pass in the initial
        # model configuration.
        if 'model_name' in llm_defaults:
            llm_defaults['model_name'] = self.backend.model
        defaults = {k: v for k, v in llm_defaults.items() if k in custom_config}
        return defaults

    def calculate_customization_value(self, orig_keys, new_value):
        if isinstance(orig_keys, str):
            orig_keys = orig_keys.split('.')
        keys = orig_keys.copy()
        config = self.customization_config()
        while keys:
            key = keys.pop(0)
            if key in config:
                config = config[key]
                if config == dict:
                    return True, new_value, "Found dict key."
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
            keys = keys.split('.')
        customizations = self.customizations.copy()
        while keys:
            key = keys.pop(0)
            if key in customizations:
                customizations = customizations[key]
                if not isinstance(customizations, dict):
                    return True, customizations, f"Found key {key}"
        return False, None, f"Invalid key {key}."

    def set_customization_value(self, keys, new_value):
        if isinstance(keys, str):
            keys = keys.split('.')
        success, new_value, user_message = self.calculate_customization_value(keys, new_value)
        if success:
            self.set_value(keys, new_value)
            return success, self.customizations, f"Set {'.'.join(keys)} to {new_value}"
        else:
            return success, new_value, user_message

    def set_value(self, keys, value):
        customizations = self.customizations
        for key in keys[:-1]:
            customizations = customizations.setdefault(key, {})
        customizations[keys[-1]] = value

    def set_customizations(self, customizations):
        self.customizations = customizations

    def customizations_to_completions(self):
        def dict_to_completions(completions, items, prefix=[], is_dict=False):
            for key, value in items.items():
                full_key = '.'.join(prefix + [key])
                if value == dict:
                    completions[full_key] = {}
                elif isinstance(value, dict):
                    prefix.append(key)
                    completions[full_key] = None
                    for k, v in value.items():
                        dict_key = "%s.%s" % (full_key, k)
                        if isinstance(v, PresetValue):
                            completions[dict_key] = v.completions
                        else:
                            completions[dict_key] = None
                    dict_to_completions(completions, value, prefix, is_dict)
                elif isinstance(value, PresetValue):
                    completions[full_key] = value.completions
                else:
                    completions[full_key] = value
            return completions
        completions = dict_to_completions({}, self.customization_config())
        return completions

    def get_shell_completions(self, base_shell_completions):
        base_shell_completions[util.command_with_leader('model')] = self.customizations_to_completions()

    def make_llm(self, customizations=None):
        final_customizations = copy.deepcopy(self.customizations)
        if customizations:
            final_customizations.update(customizations)
        llm_class = self.llm_factory()
        llm = llm_class(**final_customizations)
        return llm

class Provider(ProviderBase):

    @abstractmethod
    def max_submission_tokens(self):
        pass

    @abstractmethod
    def llm_factory(self):
        pass

    @abstractmethod
    def customization_config(self):
        pass
