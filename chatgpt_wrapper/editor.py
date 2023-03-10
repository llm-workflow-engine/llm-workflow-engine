import os
import tempfile
import subprocess
import platform

import chatgpt_wrapper.debug as debug
if False:
    debug.console(None)

SYSTEM = platform.system()

WINDOWS_EDITOR_BINARIES = ['notepad++.exe', 'WordPad.exe', 'notepad']
LINUX_EDITOR_VIM_BINARIES = ['vim', 'nvim']

def get_linux_editor():
    editor = os.environ.get('VISUAL', os.environ.get('EDITOR', 'vi'))
    executable = os.path.basename(editor)
    return editor, executable

def discover_editor():
    command_parts = []
    if SYSTEM == 'Windows':
        editor_path = None
        for editor in WINDOWS_EDITOR_BINARIES:
            try:
                editor_path = subprocess.check_output(f"where {editor}", shell=True).decode().strip()
                break
            except subprocess.CalledProcessError:
                continue
        if editor_path:
            command_parts = [editor_path]
        else:
            raise Exception("No Windows editor found, tried: " + ", ".join(WINDOWS_EDITOR_BINARIES))
    elif SYSTEM == 'Darwin':
        command_parts = ['open', '-t']
    else:
        editor_path, executable = get_linux_editor()
        command_parts = [editor_path]
        # Little extra sauce for Vim users.
        if executable in LINUX_EDITOR_VIM_BINARIES:
            command_parts.extend(['-c', 'set filetype=markdown'])
    return command_parts

def open_temp_file(input_data='', suffix=None):
    kwargs = {'suffix': f'.{suffix}'} if suffix else {}
    _, filepath = tempfile.mkstemp(**kwargs)
    with open(filepath, 'w') as f:
        f.write(input_data)
    return filepath

def file_editor(filepath):
    command_parts = discover_editor()
    command_parts.append(filepath)
    subprocess.run(command_parts, check=True)

def pipe_editor(input_data='', suffix=None):
    filepath = open_temp_file(input_data, suffix)
    file_editor(filepath)
    with open(filepath, 'r') as f:
        output_data = f.read()
    os.remove(filepath)
    return output_data
