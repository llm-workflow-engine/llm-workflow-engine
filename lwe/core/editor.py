import os
import subprocess
import platform

import lwe.core.util as util

SYSTEM = platform.system()


def get_environment_editor(default=None):
    """
    Fetches the preferred editor from the environment variables.

    This function checks the environment variables 'VISUAL' and 'EDITOR' in order to determine the user's preferred editor.
    If neither of these variables are set, it returns a default value.

    :param default: The default editor to return if no environment variable is set.
    :type default: str or None
    :return: The preferred editor as specified by environment variables or the default value.
    :rtype: str or None
    """
    editor = os.environ.get("VISUAL", os.environ.get("EDITOR", default))
    return editor


def discover_editor():
    command_parts = []
    if SYSTEM == "Windows":
        editor_path = get_environment_editor("notepad")
        command_parts = [editor_path]
    elif SYSTEM == "Darwin":
        editor_path = get_environment_editor()
        command_parts = [editor_path] if editor_path else ["open", "-t"]
    else:
        editor_path = get_environment_editor("vi")
        command_parts = [editor_path]
    return command_parts


def file_editor(filepath):
    command_parts = discover_editor()
    command_parts.append(filepath)
    subprocess.call(command_parts)


def pipe_editor(input_data="", suffix=None):
    filepath = util.write_temp_file(input_data, suffix)
    file_editor(filepath)
    with open(filepath, "r") as f:
        output_data = f.read()
    try:
        os.remove(filepath)
    except PermissionError:
        util.print_status_message(False, f"WARNING: Unable to delete temporary file {filepath!r}. You may need to delete it manually.")
    return output_data
