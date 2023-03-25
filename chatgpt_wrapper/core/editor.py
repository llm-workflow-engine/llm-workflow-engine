import os
import subprocess
import platform

import chatgpt_wrapper.core.util as util

SYSTEM = platform.system()

WINDOWS_EDITORS = ['micro', 'nano', 'vim']

def get_environment_editor(default=None):
    editor = os.environ.get('VISUAL', os.environ.get('EDITOR', default))
    return editor

def discover_editor():
    command_parts = []
    if SYSTEM == 'Windows':
        editor_executable = get_environment_editor()
        executables_search = editor_executable and [editor_executable] or WINDOWS_EDITORS
        for editor in executables_search:
            try:
                editor_paths = subprocess.check_output(f"where {editor}", shell=True).decode().strip()
                break
            except subprocess.CalledProcessError:
                continue
        if editor_paths:
            editor_path = editor_paths.split("\r")[0].strip()
            command_parts = [editor_path]
        else:
            raise Exception("No Windows editor found, tried: " + ", ".join(WINDOWS_EDITORS))
    elif SYSTEM == 'Darwin':
        editor_path = get_environment_editor()
        command_parts = [editor_path] if editor_path else ['open', '-t']
    else:
        editor_path = get_environment_editor('vi')
        command_parts = [editor_path]
    return command_parts

def file_editor(filepath):
    command_parts = discover_editor()
    command_parts.append(filepath)
    subprocess.call(command_parts)

def pipe_editor(input_data='', suffix=None):
    filepath = util.open_temp_file(input_data, suffix)
    file_editor(filepath)
    with open(filepath, 'r') as f:
        output_data = f.read()
    # This is ugly, but Windows is throwing an error on deletion of the temp file.
    if SYSTEM == 'Windows':
        print(f"Deletion of temporary files on Windows is not currently supported, editor content was saved to '{filepath}', and can be deleted manually if desired")
        print("If you'd like to help fix this issue, see https://github.com/mmabrouk/chatgpt-wrapper/issues/224")
    else:
        os.remove(filepath)
    return output_data
