import re
import textwrap
import yaml
import os
import platform
import sys
import shutil
import signal
import pyperclip
import frontmatter

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
# from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import NestedCompleter, PathCompleter
from prompt_toolkit.styles import Style
import prompt_toolkit.document as document

from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound, meta

from rich.console import Console
from rich.markdown import Markdown

import chatgpt_wrapper.constants as constants
from chatgpt_wrapper.config import Config
from chatgpt_wrapper.logger import Logger
from chatgpt_wrapper.editor import file_editor, pipe_editor
from chatgpt_wrapper.plugin_manager import PluginManager
import chatgpt_wrapper.debug as debug
if False:
    debug.console(None)

is_windows = platform.system() == "Windows"

# Monkey patch _FIND_WORD_RE in the document module.
# This is needed because the current version of _FIND_WORD_RE
# doesn't allow any special characters in the first word, and we need
# to start commands with a special character.
# It would also be possible to subclass NesteredCompleter and override
# the get_completions() method, but that feels more brittle.
document._FIND_WORD_RE = re.compile(r"([a-zA-Z0-9-" + constants.COMMAND_LEADER + r"]+|[^a-zA-Z0-9_\s]+)")
# I think this 'better' regex should work, but it's not.
# document._FIND_WORD_RE = re.compile(r"(\/|\/?[a-zA-Z0-9_]+|[^a-zA-Z0-9_\s]+)")

class LegacyCommandLeaderError(Exception):
    pass

class NoInputError(Exception):
    pass

class GPTShell():
    """
    A shell interpreter that serves as a front end to the ChatGPT class
    """

    intro = "Provide a prompt for ChatGPT, or type %shelp or ? to list commands." % constants.COMMAND_LEADER
    prompt = "> "
    prompt_prefix = ""
    doc_header = "Documented commands type %shelp [command without %s] (e.g. /help ask) for detailed help" % (constants.COMMAND_LEADER, constants.COMMAND_LEADER)

    # our stuff
    prompt_number = 0
    chatgpt = None
    message_map = {}
    stream = False
    logfile = None

    def __init__(self, config=None):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.console = Console()
        self.template_dirs = self.make_template_dirs()
        self.templates = []
        self.templates_env = None
        self.history = self.get_history()
        self.style = self.get_styles()
        self.prompt_session = PromptSession(
            history=self.history,
            # NOTE: Suggestions from history don't seem like a good fit for this REPL,
            # so we don't use it. Leaving it here for reference.
            # auto_suggest=AutoSuggestFromHistory(),
            style=self.style,
        )
        self.stream = self.config.get('chat.streaming')
        self._set_logging()
        self._setup_signal_handlers()

    def terminate_stream(self, _signal, _frame):
        self.backend.terminate_stream(_signal, _frame)

    def _setup_signal_handlers(self):
        sig = is_windows and signal.SIGBREAK or signal.SIGUSR1
        signal.signal(sig, self.terminate_stream)

    def exec_prompt_pre(self, _command, _arg):
        pass

    def introspect_commands(self, klass):
        return [method[3:] for method in dir(klass) if callable(getattr(klass, method)) and method.startswith("do_")]

    def configure_shell_commands(self):
        self.commands = self.introspect_commands(__class__)

    def get_plugin_commands(self):
        commands = []
        for plugin in self.plugins.values():
            plugin_commands = self.introspect_commands(plugin.__class__)
            commands.extend(plugin_commands)
        return commands

    def configure_commands(self):
        self.commands.extend(self.get_plugin_commands())
        self.dashed_commands = [self.underscore_to_dash(command) for command in self.commands]
        self.dashed_commands.sort()
        self.all_commands = self.dashed_commands + ['help']
        self.all_commands.sort()

    def command_with_leader(self, command):
        key = "%s%s" % (constants.COMMAND_LEADER, command)
        return key

    def merge_dicts(self, dict1, dict2):
        for key in dict2:
            if key in dict1 and isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                self.merge_dicts(dict1[key], dict2[key])
            else:
                dict1[key] = dict2[key]
        return dict1

    def get_custom_shell_completions(self):
        return {}

    def get_plugin_shell_completions(self, completions):
        for plugin in self.plugins.values():
            plugin_completions = plugin.get_shell_completions(self.base_shell_completions)
            if plugin_completions:
                completions = self.merge_dicts(completions, plugin_completions)
        return completions

    def underscore_to_dash(self, text):
        return text.replace("_", "-")

    def dash_to_underscore(self, text):
        return text.replace("-", "_")

    def set_base_shell_completions(self):
        commands_with_leader = {}
        for command in self.all_commands:
            commands_with_leader[self.command_with_leader(command)] = None
        commands_with_leader[self.command_with_leader('help')] = self.list_to_completion_hash(self.dashed_commands)
        for command in ['file', 'log']:
            commands_with_leader[self.command_with_leader(command)] = PathCompleter()
        commands_with_leader[self.command_with_leader('model')] = self.list_to_completion_hash(self.backend.available_models.keys())
        template_completions = self.list_to_completion_hash(self.templates)
        template_commands = [c for c in self.dashed_commands if c.startswith('template') and c != 'templates']
        for command in template_commands:
            commands_with_leader[self.command_with_leader(command)] = template_completions
        self.base_shell_completions = commands_with_leader

    def list_to_completion_hash(self, completion_list):
        completions = {str(val): None for val in completion_list}
        return completions

    def rebuild_completions(self):
        self.set_base_shell_completions()
        completions = self.merge_dicts(self.base_shell_completions, self.get_custom_shell_completions())
        completions = self.get_plugin_shell_completions(completions)
        self.command_completer = NestedCompleter.from_nested_dict(completions)

    def validate_int(self, value, min=None, max=None):
        try:
            value = int(value)
        except ValueError:
            return False
        if min and value < min:
            return False
        if max and value > max:
            return False
        return value

    def validate_float(self, value, min=None, max=None):
        try:
            value = float(value)
        except ValueError:
            return False
        if min and value < min:
            return False
        if max and value > max:
            return False
        return value

    def validate_str(self, value, min=None, max=None):
        try:
            value = str(value)
        except ValueError:
            return False
        if min and len(value) < min:
            return False
        if max and len(value) > max:
            return False
        return value

    def get_history(self):
        return FileHistory(constants.COMMAND_HISTORY_FILE)

    def get_styles(self):
        style = Style.from_dict({
            'completion-menu.completion': 'bg:#008888 #ffffff',
            'completion-menu.completion.current': 'bg:#00aaaa #000000',
            'scrollbar.background': 'bg:#88aaaa',
            'scrollbar.button': 'bg:#222222',
        })
        return style

    def paste_from_clipboard(self):
        value = pyperclip.paste()
        return value

    def template_builtin_variables(self):
        return {
            'clipboard': self.paste_from_clipboard,
        }

    def ensure_template(self, template_name):
        if not template_name:
            return False, None, "No template name specified"
        self.log.debug(f"Ensuring template {template_name} exists")
        self.load_templates()
        if template_name not in self.templates:
            return False, template_name, f"Template '{template_name}' not found"
        message = f"Template {template_name} exists"
        self.log.debug(message)
        return True, template_name, message

    def extract_template_run_overrides(self, metadata):
        keys = [
            'title',
            'description',
            'model_customizations',
        ]
        overrides = {}
        for key in keys:
            if key in metadata:
                overrides[key] = metadata[key]
                del metadata[key]
        return metadata, overrides

    async def run_template(self, template_name, substitutions={}):
        template, _ = self.get_template_and_variables(template_name)
        source = frontmatter.load(template.filename)
        template_substitutions, overrides = self.extract_template_run_overrides(source.metadata)
        final_substitutions = {**template_substitutions, **substitutions}
        self.log.debug(f"Rendering template: {template_name}")
        final_template = Template(source.content)
        message = final_template.render(**final_substitutions)
        self.log.info(f"Running template: {template_name}")
        print("")
        print(message)
        return await self.default(message, **overrides)

    async def collect_template_variable_values(self, template_name, variables=[]):
        builtin_variables = self.template_builtin_variables()
        variables = list(variables)
        variables.extend(builtin_variables.keys())
        # Remove dups.
        variables = list(set(variables))
        await self.do_template(template_name)
        self._print_markdown("##### Enter variables:\n")
        self.log.debug(f"Collecting variable values for: {template_name}")
        substitutions = {}
        for variable in variables:
            if variable in builtin_variables:
                value = builtin_variables[variable]()
            else:
                value = input(f"    {variable}: ").strip()
            substitutions[variable] = value
            self.log.debug(f"Collected variable {variable} for template {template_name}: {value}")
        return substitutions

    def make_template_dirs(self):
        template_dirs = []
        template_dirs.append(os.path.join(self.config.config_dir, 'templates'))
        template_dirs.append(os.path.join(self.config.config_profile_dir, 'templates'))
        for template_dir in template_dirs:
            if not os.path.exists(template_dir):
                os.makedirs(template_dir)
        return template_dirs

    def load_templates(self):
        self.log.debug("Loading templates from dirs: %s" % ", ".join(self.template_dirs))
        jinja_env = Environment(loader=FileSystemLoader(self.template_dirs))
        filenames = jinja_env.list_templates()
        self.templates_env = jinja_env
        self.templates = filenames or []

    def get_template_and_variables(self, template_name):
        try:
            template = self.templates_env.get_template(template_name)
        except TemplateNotFound:
            return None, None
        template_source = self.templates_env.loader.get_source(self.templates_env, template_name)
        parsed_content = self.templates_env.parse(template_source)
        variables = meta.find_undeclared_variables(parsed_content)
        return template, variables

    def legacy_command_leader_warning(self, command):
        print("\nWarning: The legacy command leader '%s' has been removed.\n"
              "Use the new command leader '%s' instead, e.g. %s%s\n" % (
                  constants.LEGACY_COMMAND_LEADER, constants.COMMAND_LEADER, constants.COMMAND_LEADER, command))

    def get_command_help_brief(self, command):
        help_brief = "    %s%s" % (constants.COMMAND_LEADER, command)
        help_doc = self.get_command_help(command)
        if help_doc:
            first_line = next(filter(lambda x: x.strip(), help_doc.splitlines()), "")
            help_brief += ": %s" % first_line
        return help_brief

    def get_command_help(self, command):
        command = self.dash_to_underscore(command)
        if command in self.commands:
            method, _obj = self.get_command_method(command)
            doc = method.__doc__
            if doc:
                doc = doc.replace("{COMMAND}", "%s%s" % (constants.COMMAND_LEADER, command))
                for sub in constants.HELP_TOKEN_VARIBALE_SUBSTITUTIONS:
                    try:
                        const_value = getattr(constants, sub)
                    except AttributeError:
                        raise AttributeError(f"'{sub}' in HELP_TOKEN_VARIBALE_SUBSTITUTIONS is not a valid constant")
                    doc = doc.replace("{%s}" % sub, str(const_value))
                return textwrap.dedent(doc)

    def help_commands(self):
        print("")
        self._print_markdown(f"#### {self.doc_header}")
        print("")
        for command in self.dashed_commands:
            print(self.get_command_help_brief(command))
        print("")

    def help(self, command=''):
        if command:
            help_doc = self.get_command_help(command)
            if help_doc:
                print(help_doc)
            else:
                print("\nNo help for '%s'\n\nAvailable commands: %s" % (command, ", ".join(self.dashed_commands)))
        else:
            self.help_commands()

    def _set_logging(self):
        if self.config.get('chat.log.enabled'):
            log_file = self.config.get('chat.log.filepath')
            if log_file:
                if not self._open_log(log_file):
                    print("\nERROR: could not open log file: %s" % log_file)
                    sys.exit(0)

    def _set_prompt(self, prefix=''):
        self.prompt = f"{self.prompt_prefix}{self.prompt_number}> "

    def _set_prompt_prefix(self, prefix=''):
        self.prompt_prefix = prefix

    def _update_message_map(self):
        self.prompt_number += 1
        self.message_map[self.prompt_number] = (
            self.backend.conversation_id,
            self.backend.parent_message_id,
        )
        self._set_prompt()

    def _print_status_message(self, success, message):
        self.console.print(message, style="bold green" if success else "bold red")
        print("")

    def _print_markdown(self, output):
        self.console.print(Markdown(output))
        print("")

    def _write_log(self, prompt, response):
        if self.logfile is not None:
            self.logfile.write(f"{self.prompt_number}> {prompt}\n\n{response}\n\n")
            self._write_log_context()

    def _write_log_context(self):
        if self.logfile is not None:
            self.logfile.write(
                f"## context {self.backend.conversation_id}:{self.backend.parent_message_id}\n"
            )
            self.logfile.flush()

    def _parse_conversation_ids(self, id_string):
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

    def set_user_prompt(self):
        pass

    def configure_plugins(self):
        self.plugin_manager = PluginManager(self.config, self.backend)
        self.plugins = self.plugin_manager.get_plugins()
        for plugin in self.plugins.values():
            plugin.set_shell(self)

    async def configure_backend():
        raise NotImplementedError

    async def launch_backend():
        raise NotImplementedError

    async def setup(self):
        await self.configure_backend()
        self.configure_plugins()
        self.load_templates()
        self.configure_shell_commands()
        self.configure_commands()
        self.rebuild_completions()
        self._update_message_map()

    async def cleanup(self):
        pass

    def _conversation_from_messages(self, messages):
        message_parts = []
        for message in messages:
            message_parts.append("**%s**:" % message['role'].capitalize())
            message_parts.append(message['message'])
        content = "\n\n".join(message_parts)
        return content

    async def _fetch_history(self, limit=constants.DEFAULT_HISTORY_LIMIT, offset=0):
        self._print_markdown("* Fetching conversation history...")
        success, history, message = await self.backend.get_history(limit=limit, offset=offset)
        return success, history, message

    async def _set_title(self, title, conversation=None):
        self._print_markdown("* Setting title...")
        success, _, message = await self.backend.set_title(title, conversation['id'])
        if success:
            return success, conversation, f"Title set to: {conversation['title']}"
        else:
            return success, conversation, message

    async def _delete_conversation(self, id, label=None):
        if id == self.backend.conversation_id:
            await self._delete_current_conversation()
        else:
            label = label or id
            self._print_markdown("* Deleting conversation: %s" % label)
            success, conversation, message = await self.backend.delete_conversation(id)
            if success:
                self._print_status_message(True, f"Deleted conversation: {label}")
            else:
                self._print_status_message(False, f"Failed to deleted conversation: {label}, {message}")

    async def _delete_current_conversation(self):
        self._print_markdown("* Deleting current conversation")
        success, conversation, message = await self.backend.delete_conversation()
        if success:
            self._print_status_message(True, "Deleted current conversation")
            await self.do_new(None)
        else:
            self._print_status_message(False, "Failed to delete current conversation")


    async def do_stream(self, _):
        """
        Toggle streaming mode

        Streaming mode: streams the raw response from ChatGPT (no markdown rendering)
        Non-streaming mode: Returns full response at completion (markdown rendering supported).

        Examples:
            {COMMAND}
        """
        self.stream = not self.stream
        self._print_markdown(
            f"* Streaming mode is now {'enabled' if self.stream else 'disabled'}."
        )

    async def do_new(self, _):
        """
        Start a new conversation

        Examples:
            {COMMAND}
        """
        self.backend.new_conversation()
        self._print_markdown("* New conversation started.")
        self._update_message_map()
        self._write_log_context()

    async def do_delete(self, arg):
        """
        Delete one or more conversations

        Can delete by conversation ID, history ID, or current conversation.

        Arguments:
            conversation_id: The ID of the conversation
            history_id : The history ID

        Arguments can be mixed and matched as in the examples below.

        Examples:
            Current conversation: {COMMAND}
            By conversation ID: {COMMAND} 5eea79ce-b70e-11ed-b50e-532160c725b2
            By history ID: {COMMAND} 3
            Multiple IDs: {COMMAND} 1,5
            Ranges: {COMMAND} 1-5
            Complex: {COMMAND} 1,3-5,5eea79ce-b70e-11ed-b50e-532160c725b2
        """
        if arg:
            result = self._parse_conversation_ids(arg)
            if isinstance(result, list):
                success, conversations, message = await self._fetch_history()
                if success:
                    history_list = [c for c in conversations.values()]
                    for item in result:
                        if isinstance(item, str) and len(item) == 36:
                            await self._delete_conversation(item)
                        else:
                            if item <= len(history_list):
                                conversation = history_list[item - 1]
                                await self._delete_conversation(conversation['id'], conversation['title'])
                            else:
                                self._print_status_message(False, f"Cannont delete history item {item}, does not exist")
                else:
                    return success, conversations, message
            else:
                return False, None, result
        else:
            await self._delete_current_conversation()

    async def do_history(self, arg):
        """
        Show recent conversation history

        Arguments;
            limit: limit the number of messages to show (default {DEFAULT_HISTORY_LIMIT})
            offset: offset the list of messages by this number

        Examples:
            {COMMAND}
            {COMMAND} 10
            {COMMAND} 10 5
        """
        limit = constants.DEFAULT_HISTORY_LIMIT
        offset = 0
        if arg:
            args = arg.split(' ')
            if len(args) > 2:
                self._print_markdown("* Invalid number of arguments, must be limit [offest]")
                return
            else:
                try:
                    limit = int(args[0])
                except ValueError:
                    self._print_markdown("* Invalid limit, must be an integer")
                    return
                if len(args) == 2:
                    try:
                        offset = int(args[1])
                    except ValueError:
                        self._print_markdown("* Invalid offset, must be an integer")
                        return
        success, history, message = await self._fetch_history(limit=limit, offset=offset)
        if success:
            history_list = [h for h in history.values()]
            self._print_markdown("## Recent history:\n\n%s" % "\n".join(["1. %s: %s (%s)%s" % (h['created_time'].strftime("%Y-%m-%d %H:%M"), h['title'] or constants.NO_TITLE_TEXT, h['id'], ' (✓)' if h['id'] == self.backend.conversation_id else '') for h in history_list]))
        else:
            return success, history, message

    async def do_nav(self, arg):
        """
        Navigate to a past point in the conversation

        Arguments:
            id: prompt ID

        Examples:
            {COMMAND} 2
        """

        try:
            msg_id = int(arg)
        except Exception:
            self._print_markdown("The argument to nav must be an integer.")
            return

        if msg_id == self.prompt_number:
            self._print_markdown("You are already using prompt {msg_id}.")
            return

        if msg_id not in self.message_map:
            self._print_markdown(
                "The argument to `nav` contained an unknown prompt number."
            )
            return
        elif self.message_map[msg_id][0] is None:
            self._print_markdown(
                f"Cannot navigate to prompt number {msg_id}, no conversation present, try next prompt."
            )
            return

        (
            self.backend.conversation_id,
            self.backend.parent_message_id,
        ) = self.message_map[msg_id]
        self._update_message_map()
        self._write_log_context()
        self._print_markdown(
            f"* Prompt {self.prompt_number} will use the context from prompt {arg}."
        )

    async def do_title(self, arg):
        """
        Show or set title

        Arguments:
            title: title of the current conversation
            ...or...
            history_id: history ID of conversation

        Examples:
            Get current conversation title: {COMMAND}
            Set current conversation title: {COMMAND} new title
            Set conversation title using history ID: {COMMAND} 1
        """
        if arg:
            success, conversations, message = await self._fetch_history()
            if success:
                history_list = [c for c in conversations.values()]
                conversation = None
                id = None
                try:
                    id = int(arg)
                except Exception:
                    pass
                if id:
                    if id <= len(history_list):
                        conversation = history_list[id - 1]
                    else:
                        return False, conversations, "Cannot set title on history item %d, does not exist" % id
                    new_title = input("Enter new title for '%s': " % conversation["title"] or constants.NO_TITLE_TEXT)
                else:
                    if self.backend.conversation_id in conversations:
                        conversation = conversations[self.backend.conversation_id]
                    else:
                        success, conversation, message = await self.backend.get_conversation(self.backend.conversation_id)
                        if not success:
                            return success, conversations, message
                    new_title = arg
                # Browser backend doesn't return a full conversation object,
                # so adjust and re-use the current one.
                conversation['title'] = new_title
                return await self._set_title(new_title, conversation)
            else:
                return success, conversations, message
        else:
            if self.backend.conversation_id:
                success, conversations, message = await self._fetch_history()
                if success:
                    if self.backend.conversation_id in conversations:
                        self._print_markdown("* Title: %s" % conversations[self.backend.conversation_id]['title'] or constants.NO_TITLE_TEXT)
                    else:
                        return False, conversations, "Cannot load conversation title, not in history"
                else:
                    return success, conversations, message
            else:
                return False, None, "Current conversation has no title, you must send information first"

    async def do_chat(self, arg):
        """
        Retrieve chat content

        Arguments:
            conversation_id: The ID of the conversation
            ...or...
            history_id: The history ID
            With no arguments, show content of the current conversation.

        Examples:
            Current conversation: {COMMAND}
            By conversation ID: {COMMAND} 5eea79ce-b70e-11ed-b50e-532160c725b2
            By history ID: {COMMAND} 2
        """
        conversation = None
        conversation_id = None
        title = None
        if arg:
            if len(arg) == 36:
                conversation_id = arg
                title = arg
            else:
                success, conversations, message = await self._fetch_history()
                if success:
                    history_list = [h for h in conversations.values()]
                    id = None
                    try:
                        id = int(arg)
                    except Exception:
                        return False, conversations, f"Invalid chat history item {id}, must be in integer"
                    if id <= len(history_list):
                        conversation = history_list[id - 1]
                        title = conversation["title"] or constants.NO_TITLE_TEXT
                    else:
                        return False, conversations, f"Cannot retrieve chat content on history item {id}, does not exist"
                else:
                    return success, conversations, message
        else:
            if self.backend.conversation_id:
                conversation_id = self.backend.conversation_id
            else:
                return False, None, "Current conversation is empty, you must send information first"
        if conversation:
            conversation_id = conversation["id"]
        success, conversation_data, message = await self.backend.get_conversation(conversation_id)
        if success:
            if conversation_data:
                messages = self.backend.conversation_data_to_messages(conversation_data)
                if title:
                    self._print_markdown(f"### {title}")
                self._print_markdown(self._conversation_from_messages(messages))
            else:
                return False, conversation_data, "Could not load chat content"
        else:
            return success, conversation_data, message

    async def do_switch(self, arg):
        """
        Switch to chat

        Arguments:
            conversation_id: The ID of the conversation
            ...or...
            history_id: The history ID

        Examples:
            By conversation ID: {COMMAND} 5eea79ce-b70e-11ed-b50e-532160c725b2
            By history ID: {COMMAND} 2
        """
        conversation = None
        conversation_id = None
        title = None
        if arg:
            if len(arg) == 36:
                conversation_id = arg
                title = arg
            else:
                success, conversations, message = await self._fetch_history()
                if success:
                    history_list = [c for c in conversations.values()]
                    id = None
                    try:
                        id = int(arg)
                    except Exception:
                        return False, conversations, f"Invalid chat history item {id}, must be in integer"
                    if id <= len(history_list):
                        conversation = history_list[id - 1]
                        title = conversation["title"] or constants.NO_TITLE_TEXT
                    else:
                        return False, conversations, f"Cannot retrieve chat content on history item {id}, does not exist"
                else:
                    return success, conversations, message
        else:
            return False, None, "Argument required, ID or history ID"
        if conversation:
            conversation_id = conversation["id"]
        if conversation_id == self.backend.conversation_id:
            return True, conversation, f"You are already in chat: {title}"
        success, conversation_data, message = await self.backend.get_conversation(conversation_id)
        if success:
            if conversation_data:
                messages = self.backend.conversation_data_to_messages(conversation_data)
                message = messages.pop()
                self.backend.switch_to_conversation(conversation_id, message['id'])
                self._update_message_map()
                self._write_log_context()
                if title:
                    self._print_markdown(f"### Switched to: {title}")
            else:
                return False, conversation_data, "Could not switch to chat"
        else:
            return success, conversation_data, message

    async def do_ask(self, line):
        """
        Ask a question to ChatGPT

        It is purely optional.

        Examples:
            {COMMAND} what is 6+6 (is the same as 'what is 6+6')
        """
        return await self.default(line)

    async def default(self, line, title=None, model_customizations={}):
        if not line:
            return

        if self.stream:
            response = ""
            first = True
            async for chunk in self.backend.ask_stream(line, title=title, model_customizations=model_customizations):
                if first:
                    print("")
                    first = False
                print(chunk, end="")
                sys.stdout.flush()
                response += chunk
            print("\n")
        else:
            success, response, message = await self.backend.ask(line, title=title, model_customizations=model_customizations)
            if success:
                print("")
                self._print_markdown(response)
            else:
                return success, response, message

        self._write_log(line, response)
        self._update_message_map()

    async def do_read(self, _):
        """
        Begin reading multi-line input

        Allows for entering more complex multi-line input prior to sending it to ChatGPT.

        Examples:
            {COMMAND}
        """
        ctrl_sequence = "^z" if is_windows else "^d"
        self._print_markdown(f"* Reading prompt, hit {ctrl_sequence} when done, or write line with /end.")

        prompt = ""
        while True:
            try:
                line = input()
            except EOFError:
                break
            if line == "":
                print("")
            if line == "/end":
                break
            prompt += line + "\n"

        await self.default(prompt)

    async def do_editor(self, args):
        """
        Open an editor for entering a command

        When the editor is closed, the content is sent to ChatGPT.

        Arguments:
            default_text: The default text to open the editor with

        Examples:
            {COMMAND}
            {COMMAND} some text to start with
        """
        output = pipe_editor(args, suffix='md')
        print(output)
        await self.default(output)

    async def do_file(self, arg):
        """
        Send a prompt read from the named file

        Arguments:
            file_name: The name of the file to read from

        Examples:
            {COMMAND} myprompt.txt
        """
        try:
            fileprompt = open(arg, encoding="utf-8").read()
        except Exception:
            self._print_markdown(f"Failed to read file '{arg}'")
            return
        await self.default(fileprompt)

    def _open_log(self, filename):
        try:
            if os.path.isabs(filename):
                self.logfile = open(filename, "a", encoding="utf-8")
            else:
                self.logfile = open(os.path.join(os.getcwd(), filename), "a", encoding="utf-8")
        except Exception:
            self._print_markdown(f"Failed to open log file '{filename}'.")
            return False
        return True

    async def do_log(self, arg):
        """
        Enable/disable logging to a file

        Arguments:
            file_name: The name of the file to write to

        Examples:
            Log to file: {COMMAND} mylog.txt
            Disable logging: {COMMAND}
        """
        if arg:
            if self._open_log(arg):
                self._print_markdown(f"* Logging enabled, appending to '{arg}'.")
        else:
            self.logfile = None
            self._print_markdown("* Logging is now disabled.")

    async def do_context(self, arg):
        """
        Load an old context from the log

        Arguments:
            context_string: a context string from logs

        Examples:
            {COMMAND} 67d1a04b-4cde-481e-843f-16fdb8fd3366:0244082e-8253-43f3-a00a-e2a82a33cba6
        """
        try:
            (conversation_id, parent_message_id) = arg.split(":")
            assert conversation_id == "None" or len(conversation_id) == 36
            assert len(parent_message_id) == 36
        except Exception:
            self._print_markdown("Invalid parameter to `context`.")
            return
        self._print_markdown("* Loaded specified context.")
        self.backend.conversation_id = (
            conversation_id if conversation_id != "None" else None
        )
        self.backend.parent_message_id = parent_message_id
        self._update_message_map()
        self._write_log_context()

    async def do_model(self, arg):
        """
        View or set the current LLM model

        Arguments:
            model_name: The name of the model to set
            With no arguments, view currently set model

        Examples:
            {COMMAND}
            {COMMAND} default
        """
        if arg:
            model_names = self.backend.available_models.keys()
            if arg in model_names:
                self.backend.set_active_model(arg)
                return True, self.backend.model, f"Current model updated to: {self.backend.model}"
            else:
                return False, arg, "Invalid model, must be one of: %s" % ", ".join(model_names)
        else:
            return True, self.backend.model, f"Current model: {self.backend.model}"

    async def do_templates(self, _):
        """
        List available templates

        Templates are pre-configured text content that can be customized before sending a message to the model.

        Templates are are per-profile, located in the 'templates' directory of the profile. (see {COMMAND_LEADER}config for current location)

        Examples:
            {COMMAND}
        """
        self.load_templates()
        self.rebuild_completions()
        templates = []
        for template_name in self.templates:
            content = f"* **{template_name}**"
            template, _ = self.get_template_and_variables(template_name)
            source = frontmatter.load(template.filename)
            if 'description' in source.metadata:
                content += f": *{source.metadata['description']}*"
            templates.append(content)
        self._print_markdown("## Templates:\n\n%s" % "\n".join(templates))

    async def do_template(self, template_name):
        """
        Display a template

        Arguments:
            template_name: Required. The name of the template

        Examples:
            {COMMAND} mytemplate.md
        """
        success, template_name, user_message = self.ensure_template(template_name)
        if not success:
            return success, template_name, user_message
        template, _ = self.get_template_and_variables(template_name)
        source = frontmatter.load(template.filename)
        self._print_markdown(f"\n## Template '{template_name}'")
        if source.metadata:
            self._print_markdown("\n```yaml\n%s\n```" % yaml.dump(source.metadata, default_flow_style=False))
        self._print_markdown(f"\n\n{source.content}")

    async def do_template_edit(self, template_name):
        """
        Create a new template, or edit an existing template

        Arguments:
            template_name: Required. The name of the template

        Examples:
            {COMMAND} mytemplate.md
        """
        if not template_name:
            return False, template_name, "No template name specified"
        template, _ = self.get_template_and_variables(template_name)
        if not template:
            return False, template_name, f"{template_name} does not exist"
        file_editor(template.filename)
        self.load_templates()
        self.rebuild_completions()

    async def do_template_copy(self, template_names):
        """
        Copies an existing template and saves it as a new template

        Arguments:
            template_names: Required. The name of the old and new templates separated by whitespace,

        Examples:
            {COMMAND} old_template.md new_template.md
        """
        try:
            old_name, new_name = template_names.split()
        except ValueError:
            return False, template_names, "Old and new template name required"
        template, _ = self.get_template_and_variables(old_name)
        if not template:
            return False, template_names, f"{old_name} does not exist"
        old_filepath = template.filename
        new_filepath = os.path.join(os.path.dirname(old_filepath), new_name)
        if os.path.exists(new_filepath):
            return False, template_names, f"{new_name} already exists"
        shutil.copy2(old_filepath, new_filepath)
        self.load_templates()
        self.rebuild_completions()
        return True, template_names, f"Copied {old_name} to {new_name}"

    async def do_template_delete(self, template_name):
        """
        Deletes an existing template

        Arguments:
            template_name: Required. The name of the template to delete

        Examples:
            {COMMAND} mytemplate.md
        """
        if not template_name:
            return False, template_name, "No template name specified"
        template, _ = self.get_template_and_variables(template_name)
        if not template:
            return False, template_name, f"{template_name} does not exist"
        confirmation = input(f"Are you sure you want to delete template {template_name}? [y/N] ").strip()
        if confirmation.lower() in ["yes", "y"]:
            os.remove(template.filename)
            self.load_templates()
            self.rebuild_completions()
            return True, template_name, f"Deleted {template_name}"
        else:
            return False, template_name, "Deletion aborted"

    async def do_template_run(self, template_name):
        """
        Run a template

        Running a template sends the content of it to the model as your input.

        Arguments:
            template_name: Required. The name of the template.

        Examples:
            {COMMAND} mytemplate.md
        """
        success, template_name, user_message = self.ensure_template(template_name)
        if not success:
            return success, template_name, user_message
        substitutions = await self.collect_template_variable_values(template_name)
        return await self.run_template(template_name, substitutions)

    async def do_template_prompt_run(self, template_name):
        """
        Prompt for template variable values, then run

        Prompts for a value for each variable in the template, sustitutes the values
        in the template, and sends the final content to the model as your input.

        Arguments:
            template_name: Required. The name of the template.

        Examples:
            {COMMAND} mytemplate.md
        """
        success, template_name, user_message = self.ensure_template(template_name)
        if not success:
            return success, template_name, user_message
        _, variables = self.get_template_and_variables(template_name)
        substitutions = await self.collect_template_variable_values(template_name, variables)
        return await self.run_template(template_name, substitutions)

    async def do_template_edit_run(self, template_name):
        """
        Open a template for final editing, then run it

        Open the template in an editor, and upon editor exit, send the final content
        to the model as your input.

        Arguments:
            template_name: Required. The name of the template.

        Examples:
            {COMMAND} mytemplate.md
        """
        success, template_name, user_message = self.ensure_template(template_name)
        if not success:
            return success, template_name, user_message
        template, _ = self.get_template_and_variables(template_name)
        substitutions = await self.collect_template_variable_values(template_name)
        message = template.render(**substitutions)
        return await self.do_editor(message)

    async def do_template_prompt_edit_run(self, template_name):
        """
        Prompts for a value for each variable in the template, sustitutes the values
        in the template, opens an editor for final edits, and sends the final content
        to the model as your input.

        Arguments:
            template_name: Required. The name of the template.

        Examples:
            {COMMAND} mytemplate.md
        """
        success, template_name, user_message = self.ensure_template(template_name)
        if not success:
            return success, template_name, user_message
        template, variables = self.get_template_and_variables(template_name)
        substitutions = await self.collect_template_variable_values(template_name, variables)
        message = template.render(**substitutions)
        return await self.do_editor(message)

    async def do_config(self, _):
        """
        Show the current configuration

        Examples:
            {COMMAND}
        """
        output = """
# Backend configuration: %s
# File configuration

* Config dir: %s
* Config profile dir: %s
* Config file: %s
* Data dir: %s
* Data profile dir: %s
* Templates dirs: %s

# Profile '%s' configuration:

```
%s
```

# Runtime configuration

* Streaming: %s
* Logging to: %s
""" % (self.config.get('backend'), self.config.config_dir, self.config.config_profile_dir, self.config.config_file or "None", self.config.data_dir, self.config.data_profile_dir, ", ".join(self.template_dirs), self.config.profile, yaml.dump(self.config.get(), default_flow_style=False), str(self.stream), self.logfile and self.logfile.name or "None")
        output += self.backend.get_runtime_config()
        self._print_markdown(output)

    async def do_exit(self, _):
        """
        Exit the ChatGPT shell

        Examples:
            {COMMAND}
        """
        pass

    async def do_quit(self, _):
        """
        Exit the ChatGPT shell

        Examples:
            {COMMAND}
        """
        pass

    def parse_shell_input(self, user_input):
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
                self.legacy_command_leader_warning(command)
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

    def get_class_command_method(self, klass, do_command):
        mro = getattr(klass, '__mro__')
        for klass in mro:
            method = getattr(klass, do_command, None)
            if method:
                return method

    def get_command_method(self, command):
        do_command = f"do_{command}"
        method = self.get_class_command_method(self.__class__, do_command)
        if method:
            return method, self
        for plugin in self.plugins.values():
            method = self.get_class_command_method(plugin.__class__, do_command)
            if method:
                return method, plugin
        raise AttributeError(f"{do_command} method not found in any shell class")

    def output_response(self, response):
        if response:
            if isinstance(response, tuple):
                success, _obj, message = response
                self._print_status_message(success, message)
            else:
                print(response)

    async def run_command(self, command, argument):
        command = self.dash_to_underscore(command)
        if command == 'help':
            self.help(argument)
        else:
            if command in self.commands:
                method, obj = self.get_command_method(command)
                try:
                    response = await method(obj, argument)
                except Exception as e:
                    print(repr(e))
                else:
                    self.output_response(response)
            else:
                print(f'Unknown command: {command}')

    async def cmdloop(self):
        print("")
        self._print_markdown("### %s" % self.intro)
        while True:
            self.set_user_prompt()
            try:
                user_input = await self.prompt_session.prompt_async(
                    self.prompt,
                    completer=self.command_completer,
                )
            except KeyboardInterrupt:
                continue  # Control-C pressed. Try again.
            except EOFError:
                break  # Control-D pressed.
            try:
                command, argument = self.parse_shell_input(user_input)
            except (NoInputError, LegacyCommandLeaderError):
                continue
            except EOFError:
                break
            exec_prompt_pre_result = self.exec_prompt_pre(command, argument)
            if exec_prompt_pre_result:
                self.output_response(exec_prompt_pre_result)
            else:
                await self.run_command(command, argument)
        print('GoodBye!')
