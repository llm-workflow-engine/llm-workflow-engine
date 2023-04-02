import os
import shutil
import sys
from datetime import datetime
import tempfile
import platform
import pyperclip

from rich.console import Console
from rich.markdown import Markdown

import chatgpt_wrapper.core.constants as constants
from chatgpt_wrapper.core.error import NoInputError, LegacyCommandLeaderError
from chatgpt_wrapper import debug
if False:
    debug.console(None)

console = Console()

is_windows = platform.system() == "Windows"

def introspect_commands(klass):
    return [method[3:] for method in dir(klass) if callable(getattr(klass, method)) and method.startswith("do_")]

def command_with_leader(command):
    key = "%s%s" % (constants.COMMAND_LEADER, command)
    return key

def legacy_command_leader_warning(command):
    print_status_message(False, "\nWarning: The legacy command leader '%s' has been removed.\n"
                                "Use the new command leader '%s' instead, e.g. %s%s\n" % (
                                    constants.LEGACY_COMMAND_LEADER, constants.COMMAND_LEADER, constants.COMMAND_LEADER, command))

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

def print_markdown(output):
    console.print(Markdown(output))
    print("")

def parse_conversation_ids(id_string):
    items = [item.strip() for item in id_string.split(',')]
    final_list = []
    for item in items:
        if len(item) == 36:
            final_list.append(item)
        else:
            sub_items = item.split('-')
            try:
                sub_items = [int(item) for item in sub_items if int(item) >= 1 and int(item) <= constants.DEFAULT_HISTORY_LIMIT]
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
    message_parts = []
    for message in messages:
        message_parts.append("**%s**:" % message['role'].capitalize())
        message_parts.append(message['message'])
    content = "\n\n".join(message_parts)
    return content

def parse_shell_input(user_input):
    text = user_input.strip()
    if not text:
        raise NoInputError
    leader = text[0]
    if leader == constants.COMMAND_LEADER or leader == constants.LEGACY_COMMAND_LEADER:
        text = text[1:]
        parts = [arg.strip() for arg in text.split(maxsplit=1)]
        command = parts[0]
        argument = parts[1] if len(parts) > 1 else ''
        if leader == constants.LEGACY_COMMAND_LEADER:
            legacy_command_leader_warning(command)
            raise LegacyCommandLeaderError
        if command == "exit" or command == "quit":
            raise EOFError
    else:
        if text == '?':
            command = 'help'
            argument = ''
        else:
            command = constants.DEFAULT_COMMAND
            argument = text
    return command, argument

def get_class_command_method(klass, do_command):
    mro = getattr(klass, '__mro__')
    for klass in mro:
        method = getattr(klass, do_command, None)
        if method:
            return method

def output_response(response):
    if response:
        if isinstance(response, tuple):
            success, _obj, message = response
            print_status_message(success, message)
        else:
            print(response)

def open_temp_file(input_data='', suffix=None):
    kwargs = {'suffix': f'.{suffix}'} if suffix else {}
    _, filepath = tempfile.mkstemp(**kwargs)
    with open(filepath, 'w') as f:
        f.write(input_data)
    return filepath

def get_package_root(obj):
    package_name = obj.__class__.__module__.split('.')[0]
    package_root = os.path.dirname(os.path.abspath(sys.modules[package_name].__file__))
    return package_root

def snake_to_class(string):
    parts = string.split('_')
    return ''.join(word.title() for word in parts)

def remove_and_create_dir(directory_path):
    if os.path.exists(directory_path):
        shutil.rmtree(directory_path)
    os.makedirs(directory_path)

def create_file(directory, filename, content=None):
    file_path = os.path.join(directory, filename)
    with open(file_path, 'w') as file:
        if content:
            file.write(content)

def current_datetime():
    now = datetime.now()
    return now
