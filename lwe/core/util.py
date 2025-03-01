import os
import re
import json
import copy
import subprocess
import inspect
import shutil
import sys
from datetime import datetime
import tempfile
import platform
import pyperclip
import urllib.parse
import glob

from rich.console import Console
from rich.markdown import Markdown

import lwe.core.constants as constants
from lwe.core.error import NoInputError

console = Console()

is_windows = platform.system() == "Windows"


class NoneAttrs:
    def __getattr__(self, _name):
        return None


def introspect_commands(klass):
    return [
        method[8:]
        for method in dir(klass)
        if callable(getattr(klass, method)) and method.startswith("command_")
    ]


def introspect_command_actions(klass, command):
    action_command = f"action_{command}_"
    prefix = len(action_command)
    return [
        method[prefix:]
        for method in dir(klass)
        if callable(getattr(klass, method)) and method.startswith(action_command)
    ]


def command_with_leader(command):
    key = "%s%s" % (constants.COMMAND_LEADER, command)
    return key


def merge_dicts(dict1, dict2):
    for key in dict2:
        if key in dict1 and isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
            merge_dicts(dict1[key], dict2[key])
        else:
            dict1[key] = dict2[key]
    return dict1


def underscore_to_dash(text):
    return text.replace("_", "-")


def dash_to_underscore(text):
    return text.replace("-", "_")


def list_to_completion_hash(completion_list):
    completions = {str(val): None for val in completion_list}
    return completions


def float_range_to_completions(min_val, max_val):
    range_list = []
    num_steps = int((max_val - min_val) * 10)
    for i in range(num_steps + 1):
        val = round((min_val + (i / 10)), 1)
        range_list.append(val)
    completions = list_to_completion_hash(range_list)
    return completions


def validate_int(value, min=None, max=None):
    try:
        value = int(value)
    except ValueError:
        return False
    if min and value < min:
        return False
    if max and value > max:
        return False
    return value


def validate_float(value, min=None, max=None):
    try:
        value = float(value)
    except ValueError:
        return False
    if min and value < min:
        return False
    if max and value > max:
        return False
    return value


def validate_str(value, min=None, max=None):
    try:
        value = str(value)
    except ValueError:
        return False
    if min and len(value) < min:
        return False
    if max and len(value) > max:
        return False
    return value


def paste_from_clipboard():
    value = pyperclip.paste()
    return value


def print_status_message(success, message, style=None):
    if style is None:
        style = "bold green" if success else "bold red"
    console.print(message, style=style)
    print("")


def print_markdown(output, style=None):
    if isinstance(output, dict):
        output = dict_to_pretty_json(output)
    console.print(Markdown(output), style=style)
    print("")


def parse_conversation_ids(id_string):
    items = [item.strip() for item in id_string.split(",")]
    final_list = []
    for item in items:
        if len(item) == 36:
            final_list.append(item)
        else:
            sub_items = item.split("-")
            try:
                sub_items = [
                    int(item)
                    for item in sub_items
                    if int(item) >= 1 and int(item) <= constants.DEFAULT_HISTORY_LIMIT
                ]
            except ValueError:
                return "Error: Invalid range, must be two ordered history numbers separated by '-', e.g. '1-10'."
            if len(sub_items) == 1:
                final_list.extend(sub_items)
            elif len(sub_items) == 2 and sub_items[0] < sub_items[1]:
                final_list.extend(list(range(sub_items[0], sub_items[1] + 1)))
            else:
                return "Error: Invalid range, must be two ordered history numbers separated by '-', e.g. '1-10'."
    return list(set(final_list))


def conversation_from_messages(messages):
    conversation_parts = []
    for message in messages:
        conversation_parts.append(
            {
                "role": message["role"],
                "display_role": "**%s**:" % message["role"].capitalize(),
                "message": message["message"],
            }
        )
    return conversation_parts


def parse_shell_input(user_input):
    text = user_input.strip()
    if not text:
        raise NoInputError
    leader = text[0]
    if leader == constants.COMMAND_LEADER:
        text = text[1:]
        parts = [arg.strip() for arg in text.split(maxsplit=1)]
        command = parts[0]
        argument = parts[1] if len(parts) > 1 else ""
        if command == "exit" or command == "quit":
            raise EOFError
    else:
        if text == "?":
            command = "help"
            argument = ""
        else:
            command = constants.DEFAULT_COMMAND
            argument = text
    return command, argument


def get_class_method(klass, command_command):
    for k in klass.__mro__:
        method = getattr(k, command_command, None)
        if method:
            return method


def dict_to_pretty_json(dict_obj):
    response = json.dumps(dict_obj, indent=4)
    return f"```json\n{response}\n```"


def output_response(response):
    if response:
        if isinstance(response, tuple):
            success, _obj, message = response
            print_status_message(success, message)
        else:
            print_markdown(response)


def write_temp_file(input_data="", suffix=None, prefix=None, dir=None):
    kwargs = {"prefix": prefix, "dir": dir}
    if suffix:
        kwargs["suffix"] = f".{suffix}"
    fd, filepath = tempfile.mkstemp(**kwargs)
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(input_data)
    except Exception:
        os.close(fd)
        raise
    return filepath


def get_package_root(obj):
    package_name = obj.__class__.__module__.split(".")[0]
    package_root = os.path.dirname(os.path.abspath(sys.modules[package_name].__file__))
    return package_root


def get_file_directory():
    filepath = inspect.stack()[1].filename
    return os.path.dirname(os.path.abspath(filepath))


def snake_to_class(string):
    parts = string.split("_")
    return "".join(word.title() for word in parts)


def remove_and_create_dir(directory_path):
    if os.path.exists(directory_path):
        shutil.rmtree(directory_path)
    os.makedirs(directory_path)


def create_file(directory, filename, content=None):
    filepath = os.path.join(directory, filename)
    with open(filepath, "w") as file:
        if content:
            file.write(content)
    return filepath


def current_datetime():
    now = datetime.now()
    return now


def filepath_replacements(filepath, config):
    filepath = filepath.replace("$HOME", os.path.expanduser("~user"))
    filepath = filepath.replace("$CONFIG_DIR", config.config_dir)
    filepath = filepath.replace("$DATA_DIR", config.data_dir)
    filepath = filepath.replace("$PROFILE", config.profile)
    return filepath


def get_environment_variable(name, default=None):
    return os.environ.get(f"LWE_{name.upper()}", default)


def get_environment_variable_list(name):
    var_list = get_environment_variable(name)
    return split_on_delimiter(var_list, ":") if var_list else None


def split_on_delimiter(string, delimiter=","):
    return [x.strip() for x in string.split(delimiter)]


def remove_prefix(text, prefix):
    pattern = r"(?i)^" + re.escape(prefix)
    return re.sub(pattern, "", text)


def get_ansible_module_doc(module_name):
    try:
        result = subprocess.run(
            ["ansible-doc", "-t", "module", module_name, "--json"],
            stdout=subprocess.PIPE,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout, strict=False)
        return data
    except subprocess.CalledProcessError as err:
        raise subprocess.CalledProcessError(f"Error parsing Ansible doc: {err}") from err
    except json.JSONDecodeError as err:
        raise json.JSONDecodeError(f"Error: Unable to parse Ansible doc: {err}") from err


def ansible_doc_to_markdown(module_name, full_doc=False):
    data = get_ansible_module_doc(module_name)
    module_data = data["copy"]["doc"]
    examples = data["copy"]["examples"]
    return_data = data["copy"]["return"]

    markdown = f"""The following is reference documentation for the Ansible {module_name!r} module.

Examples listed demonstrate how to use the module in an Ansible playbook.

"""
    markdown += f"# Description: {module_data['short_description']}"

    if full_doc:
        markdown += "\n\n## Purpose\n\n"
        for desc in module_data["description"]:
            markdown += f" * {desc}\n"

    markdown += "\n\n## Parameters\n\n"

    if full_doc:
        for option, details in module_data["options"].items():
            markdown += f"### {option}\n\n"
            for desc in details["description"]:
                markdown += f" * {desc}\n"
            if "type" in details:
                markdown += f" * Type: {details['type']}\n"
            if "default" in details:
                markdown += f" * Default: {details['default']}\n"
            markdown += "\n"
    else:
        markdown += "\n".join([f" * {k}" for k in module_data["options"].keys()])

    markdown += "\n\n##Attributes\n\n"

    if full_doc:
        for attribute, details in module_data["attributes"].items():
            markdown += f"### {attribute}\n\n"
            if isinstance(details["description"], list):
                for desc in details["description"]:
                    markdown += f" * {desc}\n"
            else:
                markdown += f"{details['description']}\n"
            markdown += "\n"
    else:
        markdown += "\n".join([f" * {k}" for k in module_data["attributes"].keys()])

    markdown += "\n\n## Return values\n\n"

    if full_doc:
        for return_value, details in return_data.items():
            markdown += f"### {return_value}\n\n"
            if isinstance(details["description"], list):
                for desc in details["description"]:
                    markdown += f" * {desc}\n"
            else:
                markdown += f"{details['description']}\n"
            markdown += f" * Type: {details['type']}\n"
            markdown += "\n"
    else:
        markdown += "\n".join([f" * {k}" for k in return_data.keys()])

    markdown += "\n\n## Examples\n\n"
    markdown += f"```yaml{examples}```\n"

    return markdown


def is_valid_url(url):
    parsed = urllib.parse.urlparse(url)
    return bool(parsed.scheme and parsed.netloc)


def list_to_markdown_list(list_obj, indent=2):
    spaces = " " * indent
    return "\n".join([f"{spaces}* {x}" for x in list_obj])


def clean_directory(directory):
    files = glob.glob(f"{directory}/*")
    for f in files:
        os.remove(f)


def transform_messages_to_chat_messages(messages):
    """
    Transform messages to chat messages.

    :param messages: List of messages
    :type messages: list
    :returns: List of chat messages
    :rtype: list
    """
    chat_messages = []
    for message in messages:
        role = message["role"]
        next_message = {
            "role": role,
        }
        if role == "assistant":
            if message["message_type"] == "tool_call":
                # NOTE: This should not be necessary, as Langchain tool intergrations
                # *should* use AIMessage.tool_calls if present, but not all do.
                # This is a workaround for those integrations that do not.
                additional_kwargs = {
                    "tool_calls": [
                        {
                            "id": tool["id"],
                            "type": "tool_calls",
                            "function": {
                                "name": tool["name"],
                                "arguments": json.dumps(tool["args"]),
                            },
                        }
                        for tool in message["message"]
                    ]
                }
                next_message["additional_kwargs"] = additional_kwargs
                next_message["tool_calls"] = message["message"]
                next_message["content"] = ""
            else:
                next_message["tool_calls"] = None
                next_message["content"] = message["message"]
        elif role == "tool":
            next_message["content"] = json.dumps(message["message"])
            next_message["name"] = (
                message["message_metadata"]["name"]
                if "name" in message["message_metadata"]
                else None
            )
            next_message["tool_call_id"] = (
                message["message_metadata"]["id"] if "id" in message["message_metadata"] else None
            )
        else:
            next_message["content"] = message["message"]
        chat_messages.append(next_message)
    return chat_messages


def extract_preset_configuration_from_request_overrides(request_overrides, active_preset_name=None):
    """
    Extracts preset configuration from the given request overrides.

    :param request_overrides: The request overrides from which to extract preset configuration.
    :return: A tuple containing a success indicator, preset/preset_overrides/activate_preset configuration, and a user message.
    """
    preset_name = None
    preset_overrides = None
    activate_preset = False
    if "preset" in request_overrides or "preset_overrides" in request_overrides:
        if "preset" in request_overrides:
            preset_name = request_overrides["preset"]
            if "activate_preset" in request_overrides and request_overrides["activate_preset"]:
                activate_preset = True
        else:
            preset_name = active_preset_name
        if not preset_name:
            return (
                False,
                (preset_name, preset_overrides, activate_preset),
                "No active preset to override",
            )
        if "preset_overrides" in request_overrides:
            preset_overrides = copy.deepcopy(request_overrides["preset_overrides"])
    return (
        True,
        (preset_name, preset_overrides, activate_preset),
        f"Extracted preset configuration from request overrides: {request_overrides}",
    )


def get_preset_name(preset):
    if preset:
        metadata, _customizations = preset
        return metadata["name"]
    return None
