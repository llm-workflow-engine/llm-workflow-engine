import os
import subprocess
import platform

import lwe.core.util as util

SYSTEM = platform.system()

WINDOWS_EDITORS = ["micro", "nano", "vim"]


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
        editor_executable = get_environment_editor()
        if (
            editor_executable
            and os.path.isfile(editor_executable)
            and os.access(editor_executable, os.X_OK)
        ):
            command_parts = [editor_executable]
        else:
            executables_search = editor_executable and [editor_executable] or WINDOWS_EDITORS
            for editor in executables_search:
                try:
                    editor_paths = (
                        subprocess.check_output(f"where {editor}", shell=True).decode().strip()
                    )
                    break
                except subprocess.CalledProcessError:
                    continue
            if editor_paths:
                editor_path = editor_paths.splitlines()[0].strip()
                command_parts = [editor_path]
            else:
                raise Exception("No Windows editor found, tried: " + ", ".join(WINDOWS_EDITORS))
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
    if SYSTEM == "Windows":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        subprocess.call(command_parts, startupinfo=si)
    else:
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
