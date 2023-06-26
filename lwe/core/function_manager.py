import os
import json
import importlib

from pathlib import Path

import langchain.tools

from lwe.core.config import Config
from lwe.core.logger import Logger
import lwe.core.util as util

LANGCHAIN_TOOL_PREFIX = "Langchain-"

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
                    filename = f"{function_name}.py"
                    if filename in os.listdir(function_dir):
                        self.log.debug(f"Loading function file {filename} from directory: {function_dir}")
                        try:
                            filepath = os.path.join(function_dir, filename)
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

    def is_langchain_tool(self, function_name):
        self.log.debug(f"Checking for Langchain tool: {function_name}")
        return function_name.lower().startswith(LANGCHAIN_TOOL_PREFIX.lower())

    def get_langchain_tool(self, function_name):
        self.log.debug(f"Loading Langchain tool: {function_name}")
        tool_name = util.remove_prefix(function_name, LANGCHAIN_TOOL_PREFIX)
        tool = getattr(langchain.tools, tool_name)
        try:
            tool_instance = tool()
            return tool_instance
        except Exception as e:
            self.log.warning(f"Could not load Langchaine tool: {function_name}: {str(e)}")
            return None

    def get_langchain_tool_spec(self, function_name):
        self.log.debug(f"Loading tool spec for Langchain tool: {function_name}")
        tool_instance = self.get_langchain_tool(function_name)
        if not tool_instance:
            raise RuntimeError(f"Langchain tool {function_name} not found")
        spec = langchain.tools.format_tool_to_openai_function(tool_instance)
        spec['name'] = function_name
        return spec

    def run_langchain_tool(self, function_name, input_data):
        self.log.debug(f"Running langchaing tool: {function_name} with data: {input_data}")
        tool_instance = self.get_langchain_tool(function_name)
        if not tool_instance:
            raise RuntimeError(f"Langchain tool {function_name} not found")
        try:
            result = tool_instance.run(input_data)
        except Exception as e:
            message = f"Error: Exception occurred while running langchain tool {function_name}: {str(e)}"
            self.log.error(message)
            return False, None, message
        message = f"Langchain tool {function_name} executed successfully, output data: {result}"
        self.log.info(message)
        return True, result, message

    def load_functions(self):
        self.log.debug("Loading functions from dirs: %s" % ", ".join(self.all_function_dirs))
        self.functions = {}
        try:
            for function_dir in self.all_function_dirs:
                if os.path.exists(function_dir) and os.path.isdir(function_dir):
                    self.log.info(f"Processing directory: {function_dir}")
                    for filename in os.listdir(function_dir):
                        filepath = os.path.join(function_dir, filename)
                        if filepath.endswith('.py'):
                            function_name = Path(filename).stem
                            self.log.debug(f"Loading function file {filename} from directory: {function_dir}")
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

    def setup_function_instance(self, function_name, function_path):
        self.log.info(f"Loading function {function_name} from {function_path}")
        try:
            spec = importlib.util.spec_from_file_location(function_name, function_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            function_class_name = util.snake_to_class(function_name)
            function_class = getattr(module, function_class_name)
            function_instance = function_class(self.config)
            function_instance.set_name(function_name)
            function_instance.set_filepath(function_path)
            return function_instance
        except Exception as e:
            self.log.error(f"Error creating function instance for {function_name}: {e}")
            raise RuntimeError(f"Error creating function instance for {function_name}") from e

    def get_function_config(self, function_name):
        self.log.debug(f"Getting config for function: {function_name}")
        if self.is_langchain_tool(function_name):
            return self.get_langchain_tool_spec(function_name)
        try:
            _success, function_path, user_message = self.load_function(function_name)
            function_instance = self.setup_function_instance(function_name, function_path)
            config = function_instance.get_config()
            return config
        except Exception as e:
            self.log.error(f"Error loading function configuration for {function_name}: {str(e)}")
            raise RuntimeError(f"Failed to load configuration for {function_name}") from e

    def run_function(self, function_name, input_data):
        if isinstance(input_data, str):
            input_data = json.loads(input_data)
        if self.is_langchain_tool(function_name):
            return self.run_langchain_tool(function_name, input_data)
        self.log.debug(f"Running function: {function_name} with data: {input_data}")
        success, function_path, user_message = self.load_function(function_name)
        if not success:
            return False, function_name, user_message
        function_instance = self.setup_function_instance(function_name, function_path)
        try:
            output_data = function_instance(**input_data)
            self.log.info(f"Function {function_name} executed successfully, output data: {output_data}")
            return True, output_data, f"Function '{function_name}' executed successfully"
        except Exception as e:
            message = f"Error: Exception occurred while executing {function_path}: {str(e)}"
            self.log.error(message)
            return False, None, message

    def is_system_function(self, filepath):
        for dir in self.system_function_dirs:
            if filepath.startswith(dir):
                return True
        return False
