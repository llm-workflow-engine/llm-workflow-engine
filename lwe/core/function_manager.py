import os
import json
import subprocess

from lwe.core.config import Config
from lwe.core.logger import Logger
import lwe.core.util as util

class FunctionManager():
    """
    Manage functions.
    """

    def __init__(self, config=None):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.user_function_dirs = self.config.args.function_dir or util.get_environment_variable_list('function_dir') or self.config.get('directories.functions')
        self.make_user_function_dirs()
        self.system_function_dirs = [
            os.path.join(util.get_package_root(self), 'functions'),
        ]
        self.all_function_dirs = self.system_function_dirs + self.user_function_dirs

    def make_user_function_dirs(self):
        for function_dir in self.user_function_dirs:
            if not os.path.exists(function_dir):
                os.makedirs(function_dir)

    def load_function(self, function_name):
        self.log.debug("Loading function from dirs: %s" % ", ".join(self.all_function_dirs))
        function_filepath = None
        try:
            for function_dir in self.all_function_dirs:
                if os.path.exists(function_dir) and os.path.isdir(function_dir):
                    self.log.info(f"Processing directory: {function_dir}")
                    if function_name in os.listdir(function_dir):
                        self.log.debug(f"Loading function file {function_name} from directory: {function_dir}")
                        try:
                            filepath = os.path.join(function_dir, function_name)
                            with open(filepath, 'r') as _:
                                function_filepath = filepath
                        except Exception as e:
                            self.log.warning(f"Can't open function file {function_name} from directory: {function_dir}: {e}")
                else:
                    message = f"Failed to load function {function_name}: Directory '{function_dir}' not found or not a directory"
                    self.log.error(message)
                    return False, None, message
        except Exception as e:
            message = f"An error occurred while loading function {function_name}: {e}"
            self.log.error(message)
            return False, None, message
        if function_filepath is not None:
            message = f"Successfully loaded function file {function_name} from directory: {function_dir}"
            self.log.info(message)
            return True, function_filepath, message
        return False, None, f"Function {function_name} not found"

    def load_functions(self):
        self.log.debug("Loading functions from dirs: %s" % ", ".join(self.all_function_dirs))
        self.functions = {}
        try:
            for function_dir in self.all_function_dirs:
                if os.path.exists(function_dir) and os.path.isdir(function_dir):
                    self.log.info(f"Processing directory: {function_dir}")
                    for function_name in os.listdir(function_dir):
                        self.log.debug(f"Loading function file {function_name} from directory: {function_dir}")
                        filepath = os.path.join(function_dir, function_name)
                        self.functions[function_name] = filepath
                else:
                    message = f"Failed to load directory '{function_dir}': not found or not a directory"
                    self.log.error(message)
                    return False, None, message
            return True, self.functions, "Successfully loaded functions"
        except Exception as e:
            message = f"An error occurred while loading functions: {e}"
            self.log.error(message)
            return False, None, message

    def run_function(self, function_name, data):
        if isinstance(data, dict):
            data = json.dumps(data)
        self.log.debug(f"Running function: {function_name} with data: {data}")
        success, function_path, user_message = self.load_function(function_name)
        if not success:
            return False, function_name, user_message
        try:
            process = subprocess.Popen(
                function_path, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate(input=data.encode())
            if process.returncode != 0:
                message = f"Function '{function_path}' returned non-zero exit code {process.returncode}, error messsage: {stderr.decode()}"
                self.log.error(message)
                return False, process.returncode, message
            stdout = stdout.decode()
            self.log.info(f"Success: {function_path} executed successfully, stdout: {stdout}")
            return True, stdout, f"Function '{function_path}' executed successfully"
        except Exception as e:
            message = f"Error: Exception occurred while executing {function_path}: {str(e)}"
            self.log.error(message)
            return False, None, message

    def is_system_function(self, filepath):
        for dir in self.system_function_dirs:
            if filepath.startswith(dir):
                return True
        return False
