import os
import subprocess
import platform
import shlex

import lwe.core.util as util

SYSTEM = platform.system()

DEFAULT_EDITOR_NIX = "vi"
DEFAULT_EDITOR_OS_X = "vim"
DEFAULT_EDITOR_WINDOWS = "notepad"


def get_environment_editor(default=None):
    """
    Fetches the preferred editor from the environment variables.

    This function checks the following environment variables in order to
    determine the user's preferred editor:

     - LWE_EDITOR
     - VISUAL
     - EDITOR

    :param default: The default editor to return if no environment variable is set.
    :type default: str or None
    :return: The preferred editor as specified by environment variables or the default value.
    :rtype: str or None
    """
    editor = os.environ.get("LWE_EDITOR", os.environ.get("VISUAL", os.environ.get("EDITOR", default)))
    return editor


def discover_editor():
    """
    Discovers and returns the appropriate editor command as a list of arguments.

    Handles cases where the editor command includes arguments, including quoted arguments
    with spaces (e.g. 'vim -c "set noswapfile"').

    :return: A list of command parts ready for subprocess execution
    :rtype: list[str]
    """
    if SYSTEM == "Windows":
        default_editor = DEFAULT_EDITOR_WINDOWS
    elif SYSTEM == "Darwin":
        default_editor = DEFAULT_EDITOR_OS_X
    else:
        default_editor = DEFAULT_EDITOR_NIX
    editor = get_environment_editor(default_editor)
    try:
        return shlex.split(editor)
    except ValueError as e:
        raise RuntimeError(f"Invalid editor command format '{editor}': {e}")


def file_editor(filepath):
    """
    Opens the specified file in the system's configured editor.

    :param filepath: Path to the file to edit
    :type filepath: str
    """
    command_parts = discover_editor()
    command_parts.append(filepath)
    subprocess.call(command_parts)


def pipe_editor(input_data="", suffix=None):
    """
    Opens the system editor with optional input data and returns the edited content.

    This function creates a temporary file with the provided input data, opens it in
    the system editor, waits for the user to make changes and close the editor, then
    reads and returns the modified content. The temporary file is deleted afterwards.

    :param input_data: Initial content to populate the editor with
    :type input_data: str
    :param suffix: Optional file extension for the temporary file (e.g. '.txt', '.md')
    :type suffix: str or None
    :return: The edited content after the editor is closed
    :rtype: str
    """
    filepath = util.write_temp_file(input_data, suffix)
    file_editor(filepath)
    with open(filepath, "r") as f:
        output_data = f.read()
    try:
        os.remove(filepath)
    except PermissionError:
        util.print_status_message(False, f"WARNING: Unable to delete temporary file {filepath!r}. You may need to delete it manually.")
    return output_data
