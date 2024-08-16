import os
import json
import importlib
import traceback

from pathlib import Path

import langchain_community.tools
from langchain_core.utils.function_calling import convert_to_openai_function

from lwe.core.config import Config
from lwe.core.logger import Logger
import lwe.core.util as util

LANGCHAIN_TOOL_PREFIX = "Langchain-"


class ToolManager:
    """
    Manage tools.
    """

    def __init__(self, config=None, additional_tools=None):
        self.config = config or Config()
        self.additional_tools = additional_tools or {}
        self.log = Logger(self.__class__.__name__, self.config)
        self.user_tool_dirs = (
            self.config.args.tools_dir
            or util.get_environment_variable_list("tool_dir")
            or self.config.get("directories.tools")
        )
        self.make_user_tool_dirs()
        self.system_tool_dirs = [
            os.path.join(util.get_package_root(self), "tools"),
        ]
        self.all_tool_dirs = self.system_tool_dirs + self.user_tool_dirs

    def make_user_tool_dirs(self):
        for tool_dir in self.user_tool_dirs:
            if not os.path.exists(tool_dir):
                os.makedirs(tool_dir)

    def load_tool(self, tool_name):
        self.log.debug("Loading tool from dirs: %s" % ", ".join(self.all_tool_dirs))
        tool_filepath = None
        try:
            for tool_dir in self.all_tool_dirs:
                if os.path.exists(tool_dir) and os.path.isdir(tool_dir):
                    self.log.debug(f"Processing directory: {tool_dir}")
                    filename = f"{tool_name}.py"
                    if filename in os.listdir(tool_dir):
                        self.log.debug(f"Loading tool file {filename} from directory: {tool_dir}")
                        try:
                            filepath = os.path.join(tool_dir, filename)
                            with open(filepath, "r") as _:
                                tool_filepath = filepath
                        except Exception as e:
                            self.log.warning(
                                f"Can't open tool file {tool_name} from directory: {tool_dir}: {e}"
                            )
                else:
                    message = f"Failed to load tool {tool_name}: Directory {tool_dir!r} not found or not a directory"
                    self.log.error(message)
                    return False, None, message
        except Exception as e:
            message = f"An error occurred while loading tool {tool_name}: {e}"
            self.log.error(message)
            return False, None, message
        if tool_filepath is not None:
            message = f"Successfully loaded tool file {tool_name} from directory: {tool_dir}"
            self.log.debug(message)
            return True, tool_filepath, message
        return False, None, f"Tool {tool_name} not found"

    def is_langchain_tool(self, tool_name):
        self.log.debug(f"Checking for Langchain tool: {tool_name}")
        return tool_name.lower().startswith(LANGCHAIN_TOOL_PREFIX.lower())

    def get_langchain_tool(self, tool_name):
        self.log.debug(f"Loading Langchain tool: {tool_name}")
        tool_name = util.remove_prefix(tool_name, LANGCHAIN_TOOL_PREFIX)
        try:
            tool = getattr(langchain_community.tools, tool_name)
            tool_instance = tool()
            return tool_instance
        except Exception as e:
            self.log.warning(f"Could not load Langchain tool: {tool_name}: {str(e)}")
            return None

    def get_langchain_tool_spec(self, tool_name):
        self.log.debug(f"Loading tool spec for Langchain tool: {tool_name}")
        tool_instance = self.get_langchain_tool(tool_name)
        if not tool_instance:
            raise RuntimeError(f"Langchain tool {tool_name} not found")
        spec = convert_to_openai_function(tool_instance)
        spec["name"] = tool_name
        return spec

    def run_langchain_tool(self, tool_name, input_data):
        self.log.debug(f"Running langchaing tool: {tool_name} with data: {input_data}")
        tool_instance = self.get_langchain_tool(tool_name)
        if not tool_instance:
            raise RuntimeError(f"Langchain tool {tool_name} not found")
        try:
            result = tool_instance.run(input_data)
        except Exception as e:
            message = (
                f"Error: Exception occurred while running langchain tool {tool_name}: {str(e)}"
            )
            self.log.error(message)
            return False, None, message
        message = f"Langchain tool {tool_name} executed successfully, output data: {result}"
        self.log.info(message)
        return True, result, message

    def load_tools(self):
        self.log.debug("Loading tools from dirs: %s" % ", ".join(self.all_tool_dirs))
        self.tools = self.additional_tools
        try:
            for tool_dir in self.all_tool_dirs:
                if os.path.exists(tool_dir) and os.path.isdir(tool_dir):
                    self.log.info(f"Processing directory: {tool_dir}")
                    for filename in os.listdir(tool_dir):
                        filepath = os.path.join(tool_dir, filename)
                        if filepath.endswith(".py"):
                            tool_name = Path(filename).stem
                            self.log.debug(
                                f"Loading tool file {filename} from directory: {tool_dir}"
                            )
                            self.tools[tool_name] = filepath
                else:
                    message = f"Failed to load directory {tool_dir!r}: not found or not a directory"
                    self.log.error(message)
                    return False, None, message
            return True, self.tools, "Successfully loaded tools"
        except Exception as e:
            message = f"An error occurred while loading tools: {e}"
            self.log.error(message)
            return False, None, message

    def setup_tool_instance(self, tool_name, tool_path):
        self.log.debug(f"Loading tool {tool_name} from {tool_path}")
        try:
            spec = importlib.util.spec_from_file_location(tool_name, tool_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            tool_class_name = util.snake_to_class(tool_name)
            tool_class = getattr(module, tool_class_name)
            tool_instance = tool_class(config=self.config)
            tool_instance.set_name(tool_name)
            tool_instance.set_filepath(tool_path)
            return tool_instance
        except Exception as e:
            self.log.error(f"Error creating tool instance for {tool_name}: {e}")
            raise RuntimeError(f"Error creating tool instance for {tool_name}") from e

    def dereference_tool_schema(self, schema, defs):
        if isinstance(schema, dict):
            if "$ref" in schema:
                ref_path = schema["$ref"].split("/")[-1]  # Get the last part after '/'
                return self.dereference_tool_schema(defs[ref_path], defs)
            else:
                for key, value in schema.items():
                    schema[key] = self.dereference_tool_schema(value, defs)
        elif isinstance(schema, list):
            return [self.dereference_tool_schema(item, defs) for item in schema]
        return schema

    def cleanup_tool_definition(self, tool):
        """Remove items that are not needed in the tool definition."""
        if "parameters" in tool:
            defs = tool["parameters"].pop("$defs", None)
            if defs:
                self.log.debug("Dereferencing $defs in tool parameters")
                tool["parameters"] = self.dereference_tool_schema(tool["parameters"], defs)
        return tool

    def get_tool_config(self, tool_name):
        self.log.debug(f"Getting config for tool: {tool_name}")
        if self.is_langchain_tool(tool_name):
            return self.get_langchain_tool_spec(tool_name)
        try:
            _success, tool_path, user_message = self.load_tool(tool_name)
            tool_instance = self.setup_tool_instance(tool_name, tool_path)
            config = self.cleanup_tool_definition(tool_instance.get_config())
            return config
        except Exception as e:
            self.log.error(f"Error loading tool configuration for {tool_name}: {str(e)}")
            raise RuntimeError(f"Failed to load configuration for {tool_name}") from e

    def get_tool(self, tool_name):
        self.log.debug(f"Getting tool: {tool_name}")
        success, tool_path, user_message = self.load_tool(tool_name)
        if not success:
            return False, tool_name, user_message
        tool_instance = self.setup_tool_instance(tool_name, tool_path)
        return True, tool_instance, f"Tool {tool_name!r} retrieved successfully"

    def run_tool(self, tool_name, input_data):
        if isinstance(input_data, str):
            input_data = json.loads(input_data, strict=False)
        if self.is_langchain_tool(tool_name):
            return self.run_langchain_tool(tool_name, input_data)
        self.log.debug(f"Running tool: {tool_name} with data: {input_data}")
        success, tool_instance, user_message = self.get_tool(tool_name)
        if not success:
            return False, tool_instance, user_message
        try:
            output_data = tool_instance(**input_data)
            self.log.info(f"Tool {tool_name} executed successfully, output data: {output_data}")
            return True, output_data, f"Tool {tool_name!r} executed successfully"
        except Exception as e:
            message = f"Error: Exception occurred while executing {tool_name}: {str(e)}"
            self.log.error(message)
            if self.config.debug:
                traceback.print_exc()
            return False, None, message

    def is_system_tool(self, filepath):
        for dir in self.system_tool_dirs:
            if filepath.startswith(dir):
                return True
        return False
