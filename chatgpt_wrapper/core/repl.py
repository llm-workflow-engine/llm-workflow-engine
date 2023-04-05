import re
import textwrap
import yaml
import os
import sys
import traceback
import shutil
import signal
import frontmatter
import pyperclip
import threading
import queue

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
# from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import NestedCompleter, PathCompleter
from prompt_toolkit.styles import Style
import prompt_toolkit.document as document

import chatgpt_wrapper.core.constants as constants
import chatgpt_wrapper.core.util as util
from chatgpt_wrapper.core.config import Config
from chatgpt_wrapper.core.logger import Logger
from chatgpt_wrapper.core.error import NoInputError, LegacyCommandLeaderError
from chatgpt_wrapper.core.editor import file_editor, pipe_editor
from chatgpt_wrapper.core.template import TemplateManager
from chatgpt_wrapper.core.plugin_manager import PluginManager

# Monkey patch _FIND_WORD_RE in the document module.
# This is needed because the current version of _FIND_WORD_RE
# doesn't allow any special characters in the first word, and we need
# to start commands with a special character.
# It would also be possible to subclass NesteredCompleter and override
# the get_completions() method, but that feels more brittle.
document._FIND_WORD_RE = re.compile(r"([a-zA-Z0-9-" + constants.COMMAND_LEADER + r"]+|[^a-zA-Z0-9_\s]+)")
# I think this 'better' regex should work, but it's not.
# document._FIND_WORD_RE = re.compile(r"(\/|\/?[a-zA-Z0-9_]+|[^a-zA-Z0-9_\s]+)")

class Repl():
    """
    A shell interpreter that serves as a front end to the backend classes
    """

    intro = "Provide a prompt, or type %shelp or ? to list commands." % constants.COMMAND_LEADER
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
        self.debug = self.config.get('log.console.level').lower() == 'debug'
        self.template_manager = TemplateManager(self.config)
        self.history = self.get_shell_history()
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

    def catch_ctrl_c(self, signum, _frame):
        self.log.debug(f'Ctrl-c hit: {signum}')
        sig = util.is_windows and signal.SIGBREAK or signal.SIGUSR1
        os.kill(os.getpid(), sig)

    def _setup_signal_handlers(self):
        sig = util.is_windows and signal.SIGBREAK or signal.SIGUSR1
        signal.signal(sig, self.terminate_stream)

    def exec_prompt_pre(self, _command, _arg):
        pass

    def configure_shell_commands(self):
        self.commands = util.introspect_commands(__class__)

    def get_plugin_commands(self):
        commands = []
        for plugin in self.plugins.values():
            plugin_commands = util.introspect_commands(plugin.__class__)
            commands.extend(plugin_commands)
        return commands

    def configure_commands(self):
        self.commands.extend(self.get_plugin_commands())
        self.dashed_commands = [util.underscore_to_dash(command) for command in self.commands]
        self.dashed_commands.sort()
        self.all_commands = self.dashed_commands + ['help']
        self.all_commands.sort()

    def get_custom_shell_completions(self):
        return {}

    def get_plugin_shell_completions(self, completions):
        for plugin in self.plugins.values():
            plugin_completions = plugin.get_shell_completions(self.base_shell_completions)
            if plugin_completions:
                completions = util.merge_dicts(completions, plugin_completions)
        return completions

    def set_base_shell_completions(self):
        commands_with_leader = {}
        for command in self.all_commands:
            commands_with_leader[util.command_with_leader(command)] = None
        config_args = ['edit'] + list(self.config.get().keys())
        commands_with_leader[util.command_with_leader('config')] = util.list_to_completion_hash(config_args)
        commands_with_leader[util.command_with_leader('help')] = util.list_to_completion_hash(self.dashed_commands)
        for command in ['file', 'log']:
            commands_with_leader[util.command_with_leader(command)] = PathCompleter()
        commands_with_leader[util.command_with_leader('model')] = util.list_to_completion_hash(self.backend.available_models.keys())
        template_completions = util.list_to_completion_hash(self.template_manager.templates)
        template_commands = [c for c in self.dashed_commands if c.startswith('template') and c != 'templates']
        for command in template_commands:
            commands_with_leader[util.command_with_leader(command)] = template_completions
        self.base_shell_completions = commands_with_leader

    def rebuild_completions(self):
        self.set_base_shell_completions()
        completions = util.merge_dicts(self.base_shell_completions, self.get_custom_shell_completions())
        completions = self.get_plugin_shell_completions(completions)
        self.command_completer = NestedCompleter.from_nested_dict(completions)

    def get_shell_history(self):
        history_file = self.config.get('shell.history_file')
        if history_file:
            return FileHistory(history_file)

    def get_styles(self):
        style = Style.from_dict({
            'completion-menu.completion': 'bg:#008888 #ffffff',
            'completion-menu.completion.current': 'bg:#00aaaa #000000',
            'scrollbar.background': 'bg:#88aaaa',
            'scrollbar.button': 'bg:#222222',
        })
        return style

    def run_template(self, template_name, substitutions={}):
        message, overrides = self.template_manager.build_message_from_template(template_name, substitutions)
        self.log.info(f"Running template: {template_name}")
        print("")
        print(message)
        return self.default(message, **overrides)

    def collect_template_variable_values(self, template_name, variables=[]):
        substitutions = {}
        builtin_variables = self.template_manager.template_builtin_variables()
        user_variables = list(set([v for v in variables if v not in builtin_variables]))
        if user_variables:
            self.do_template(template_name)
            util.print_markdown("##### Enter variables:\n")
            self.log.debug(f"Collecting variable values for: {template_name}")
            for variable in user_variables:
                substitutions[variable] = input(f"    {variable}: ").strip()
                self.log.debug(f"Collected variable {variable} for template {template_name}: {substitutions[variable]}")
        substitutions = util.merge_dicts(substitutions, self.template_manager.process_template_builtin_variables(template_name, variables))
        return substitutions

    def get_command_help_brief(self, command):
        help_brief = "    %s%s" % (constants.COMMAND_LEADER, command)
        help_doc = self.get_command_help(command)
        if help_doc:
            first_line = next(filter(lambda x: x.strip(), help_doc.splitlines()), "")
            help_brief += ": %s" % first_line
        return help_brief

    def get_command_help(self, command):
        command = util.dash_to_underscore(command)
        if command in self.commands:
            method, _obj = self.get_command_method(command)
            doc = method.__doc__
            if doc:
                doc = doc.replace("{COMMAND}", "%s%s" % (constants.COMMAND_LEADER, command))
                for sub in constants.HELP_TOKEN_VARIABLE_SUBSTITUTIONS:
                    try:
                        const_value = getattr(constants, sub)
                    except AttributeError:
                        raise AttributeError(f"'{sub}' in HELP_TOKEN_VARIABLE_SUBSTITUTIONS is not a valid constant")
                    doc = doc.replace("{%s}" % sub, str(const_value))
                return textwrap.dedent(doc)

    def help_commands(self):
        print("")
        util.print_markdown(f"#### {self.doc_header}")
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

    def build_shell_user_prefix(self):
        return ''

    def set_user_prompt(self, user=None):
        prefix = self.build_shell_user_prefix()
        self._set_prompt_prefix(prefix)
        self._set_prompt()

    def configure_plugins(self):
        self.plugin_manager = PluginManager(self.config, self.backend)
        self.plugins = self.plugin_manager.get_plugins()
        for plugin in self.plugins.values():
            plugin.set_shell(self)

    def configure_backend():
        raise NotImplementedError

    def launch_backend(self, interactive=True):
        raise NotImplementedError

    def setup(self):
        self.configure_backend()
        self.configure_plugins()
        self.template_manager.load_templates()
        self.configure_shell_commands()
        self.configure_commands()
        self.rebuild_completions()
        self._update_message_map()

    def cleanup(self):
        pass

    def _fetch_history(self, limit=constants.DEFAULT_HISTORY_LIMIT, offset=0):
        util.print_markdown("* Fetching conversation history...")
        success, history, message = self.backend.get_history(limit=limit, offset=offset)
        return success, history, message

    def _set_title(self, title, conversation=None):
        util.print_markdown("* Setting title...")
        success, _, message = self.backend.set_title(title, conversation['id'])
        if success:
            return success, conversation, f"Title set to: {conversation['title']}"
        else:
            return success, conversation, message

    def _delete_conversation(self, id, label=None):
        if id == self.backend.conversation_id:
            self._delete_current_conversation()
        else:
            label = label or id
            util.print_markdown("* Deleting conversation: %s" % label)
            success, conversation, message = self.backend.delete_conversation(id)
            if success:
                util.print_status_message(True, f"Deleted conversation: {label}")
            else:
                util.print_status_message(False, f"Failed to deleted conversation: {label}, {message}")

    def _delete_current_conversation(self):
        util.print_markdown("* Deleting current conversation")
        success, conversation, message = self.backend.delete_conversation()
        if success:
            util.print_status_message(True, "Deleted current conversation")
            self.do_new(None)
        else:
            util.print_status_message(False, "Failed to delete current conversation")


    def do_stream(self, _):
        """
        Toggle streaming mode

        Streaming mode: streams the raw response (no markdown rendering)
        Non-streaming mode: Returns full response at completion (markdown rendering supported).

        Examples:
            {COMMAND}
        """
        self.stream = not self.stream
        util.print_markdown(
            f"* Streaming mode is now {'enabled' if self.stream else 'disabled'}."
        )

    def do_new(self, _):
        """
        Start a new conversation

        Examples:
            {COMMAND}
        """
        self.backend.new_conversation()
        util.print_markdown("* New conversation started.")
        self._update_message_map()
        self._write_log_context()

    def do_delete(self, arg):
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
            result = util.parse_conversation_ids(arg)
            if isinstance(result, list):
                success, conversations, message = self._fetch_history()
                if success:
                    history_list = [c for c in conversations.values()]
                    for item in result:
                        if isinstance(item, str) and len(item) == 36:
                            self._delete_conversation(item)
                        else:
                            if item <= len(history_list):
                                conversation = history_list[item - 1]
                                self._delete_conversation(conversation['id'], conversation['title'])
                            else:
                                util.print_status_message(False, f"Cannont delete history item {item}, does not exist")
                else:
                    return success, conversations, message
            else:
                return False, None, result
        else:
            self._delete_current_conversation()

    def do_copy(self, _):
        """
        Copy last conversation message to clipboard

        Examples:
            {COMMAND}
        """
        clipboard = self.backend.message_clipboard
        if clipboard:
            pyperclip.copy(clipboard)
            return True, clipboard, "Copied last message to clipboard"
        return False, None, "No message to copy"

    def do_history(self, arg):
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
                util.print_markdown("* Invalid number of arguments, must be limit [offest]")
                return
            else:
                try:
                    limit = int(args[0])
                except ValueError:
                    util.print_markdown("* Invalid limit, must be an integer")
                    return
                if len(args) == 2:
                    try:
                        offset = int(args[1])
                    except ValueError:
                        util.print_markdown("* Invalid offset, must be an integer")
                        return
        success, history, message = self._fetch_history(limit=limit, offset=offset)
        if success:
            history_list = [h for h in history.values()]
            util.print_markdown("## Recent history:\n\n%s" % "\n".join(["1. %s: %s (%s)%s" % (h['created_time'].strftime("%Y-%m-%d %H:%M"), h['title'] or constants.NO_TITLE_TEXT, h['id'], ' (✓)' if h['id'] == self.backend.conversation_id else '') for h in history_list]))
        else:
            return success, history, message

    def do_nav(self, arg):
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
            util.print_markdown("The argument to nav must be an integer.")
            return

        if msg_id == self.prompt_number:
            util.print_markdown("You are already using prompt {msg_id}.")
            return

        if msg_id not in self.message_map:
            util.print_markdown(
                "The argument to `nav` contained an unknown prompt number."
            )
            return
        elif self.message_map[msg_id][0] is None:
            util.print_markdown(
                f"Cannot navigate to prompt number {msg_id}, no conversation present, try next prompt."
            )
            return

        (
            self.backend.conversation_id,
            self.backend.parent_message_id,
        ) = self.message_map[msg_id]
        self._update_message_map()
        self._write_log_context()
        util.print_markdown(
            f"* Prompt {self.prompt_number} will use the context from prompt {arg}."
        )

    def do_title(self, arg):
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
            id = None
            try:
                id = int(arg)
            except Exception:
                pass
            kwargs = {}
            if id:
                # TODO: History on browser backend is sometimes returning a few less items than asked for,
                # pad it for now.
                kwargs['limit'] = id + 5
                # kwargs['limit'] = id
            success, conversations, message = self._fetch_history(**kwargs)
            if success:
                history_list = [c for c in conversations.values()]
                conversation = None
                if id:
                    if id <= len(history_list):
                        conversation = history_list[id - 1]
                    else:
                        return False, conversations, "Cannot set title on history item %d, does not exist" % id
                    new_title = input("Enter new title for '%s': " % conversation["title"] or constants.NO_TITLE_TEXT)
                else:
                    if self.backend.conversation_id:
                        if self.backend.conversation_id in conversations:
                            conversation = conversations[self.backend.conversation_id]
                        else:
                            success, conversation_data, message = self.backend.get_conversation(self.backend.conversation_id)
                            if not success:
                                return success, conversation_data, message
                            conversation = conversation_data['conversation']
                        new_title = arg
                    else:
                        return False, None, "Current conversation has no title, you must send information first"
                # Browser backend doesn't return a full conversation object,
                # so adjust and re-use the current one.
                conversation['title'] = new_title
                return self._set_title(new_title, conversation)
            else:
                return success, conversations, message
        else:
            if self.backend.conversation_id:
                success, conversation_data, message = self.backend.get_conversation()
                if success:
                    util.print_markdown("* Title: %s" % conversation_data['conversation']['title'] or constants.NO_TITLE_TEXT)
                else:
                    return success, conversation_data, message
            else:
                return False, None, "Current conversation has no title, you must send information first"

    def do_chat(self, arg):
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
                id = None
                try:
                    id = int(arg)
                except Exception:
                    return False, None, f"Invalid chat history item {arg}, must be in integer"
                kwargs = {}
                if id:
                    # TODO: History on browser backend is sometimes returning a few less items than asked for,
                    # pad it for now.
                    kwargs['limit'] = id + 5
                    # kwargs['limit'] = id
                success, conversations, message = self._fetch_history(**kwargs)
                if success:
                    history_list = [h for h in conversations.values()]
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
        success, conversation_data, message = self.backend.get_conversation(conversation_id)
        if success:
            if conversation_data:
                messages = self.backend.conversation_data_to_messages(conversation_data)
                if title:
                    util.print_markdown(f"### {title}")
                util.print_markdown(util.conversation_from_messages(messages))
            else:
                return False, conversation_data, "Could not load chat content"
        else:
            return success, conversation_data, message

    def do_switch(self, arg):
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
                id = None
                try:
                    id = int(arg)
                except Exception:
                    return False, None, f"Invalid chat history item {arg}, must be in integer"
                kwargs = {}
                if id:
                    # TODO: History on browser backend is sometimes returning a few less items than asked for,
                    # pad it for now.
                    kwargs['limit'] = id + 5
                    # kwargs['limit'] = id
                success, conversations, message = self._fetch_history(**kwargs)
                if success:
                    history_list = [c for c in conversations.values()]
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
        success, conversation_data, message = self.backend.get_conversation(conversation_id)
        if success:
            if conversation_data:
                messages = self.backend.conversation_data_to_messages(conversation_data)
                message = messages.pop()
                self.backend.switch_to_conversation(conversation_id, message['id'])
                self._update_message_map()
                self._write_log_context()
                if title:
                    util.print_markdown(f"### Switched to: {title}")
            else:
                return False, conversation_data, "Could not switch to chat"
        else:
            return success, conversation_data, message

    def do_ask(self, line):
        """
        Ask a question

        It is purely optional.

        Examples:
            {COMMAND} what is 6+6 (is the same as 'what is 6+6')
        """
        return self.default(line)

    def default(self, line, title=None, model_customizations={}):
        # TODO: This signal is recognized on Windows, and calls the callback, but the entire
        # process is still killed.
        signal.signal(signal.SIGINT, self.catch_ctrl_c)
        if not line:
            return

        if self.stream:
            print("")
            success, response, user_message = self.backend.ask_stream(line, title=title, model_customizations=model_customizations)
            print("\n")
            if not success:
                return success, response, user_message
        else:
            success, response, user_message = self.backend.ask(line, title=title, model_customizations=model_customizations)
            if success:
                print("")
                util.print_markdown(response)
            else:
                return success, response, user_message

        self._write_log(line, response)
        self._update_message_map()

    def do_read(self, _):
        """
        Begin reading multi-line input

        Allows for entering more complex multi-line input prior to sending it.

        Examples:
            {COMMAND}
        """
        ctrl_sequence = "^z" if util.is_windows else "^d"
        util.print_markdown(f"* Reading prompt, hit {ctrl_sequence} when done, or write line with /end.")

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

        self.default(prompt)

    def do_editor(self, args):
        """
        Open an editor for entering a command

        When the editor is closed, the content is sent.

        Arguments:
            default_text: The default text to open the editor with

        Examples:
            {COMMAND}
            {COMMAND} some text to start with
        """
        output = pipe_editor(args, suffix='md')
        print(output)
        self.default(output)

    def do_file(self, arg):
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
            util.print_markdown(f"Failed to read file '{arg}'")
            return
        self.default(fileprompt)

    def _open_log(self, filename):
        try:
            if os.path.isabs(filename):
                self.logfile = open(filename, "a", encoding="utf-8")
            else:
                self.logfile = open(os.path.join(os.getcwd(), filename), "a", encoding="utf-8")
        except Exception:
            util.print_markdown(f"Failed to open log file '{filename}'.")
            return False
        return True

    def do_log(self, arg):
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
                util.print_markdown(f"* Logging enabled, appending to '{arg}'.")
        else:
            self.logfile = None
            util.print_markdown("* Logging is now disabled.")

    def do_context(self, arg):
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
            util.print_markdown("Invalid parameter to `context`.")
            return
        util.print_markdown("* Loaded specified context.")
        self.backend.conversation_id = (
            conversation_id if conversation_id != "None" else None
        )
        self.backend.parent_message_id = parent_message_id
        self._update_message_map()
        self._write_log_context()

    def do_model(self, arg):
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

    def do_templates(self, arg):
        """
        List available templates

        Templates are pre-configured text content that can be customized before sending a message to the model.

        They are located in the 'templates' directory in the following locations:

            - The main configuration directory
            - The profile configuration directory

        See {COMMAND_LEADER}config for current locations.

        Arguments:
            filter_string: Optional. If provided, only templates with a name or description containing the filter string will be shown.

        Examples:
            {COMMAND}
            {COMMAND} filterstring
        """
        self.template_manager.load_templates()
        self.rebuild_completions()
        templates = []
        for template_name in self.template_manager.templates:
            content = f"* **{template_name}**"
            template, _ = self.template_manager.get_template_and_variables(template_name)
            source = frontmatter.load(template.filename)
            if 'description' in source.metadata:
                content += f": *{source.metadata['description']}*"
            if not arg or arg.lower() in content.lower():
                templates.append(content)
        util.print_markdown("## Templates:\n\n%s" % "\n".join(templates))

    def do_template(self, template_name):
        """
        Display a template

        Arguments:
            template_name: Required. The name of the template

        Examples:
            {COMMAND} mytemplate.md
        """
        success, template_name, user_message = self.template_manager.ensure_template(template_name)
        if not success:
            return success, template_name, user_message
        template, _ = self.template_manager.get_template_and_variables(template_name)
        source = frontmatter.load(template.filename)
        util.print_markdown(f"\n## Template '{template_name}'")
        if source.metadata:
            util.print_markdown("\n```yaml\n%s\n```" % yaml.dump(source.metadata, default_flow_style=False))
        util.print_markdown(f"\n\n{source.content}")

    def do_template_edit(self, template_name):
        """
        Create a new template, or edit an existing template

        Arguments:
            template_name: Required. The name of the template

        Examples:
            {COMMAND} mytemplate.md
        """
        if not template_name:
            return False, template_name, "No template name specified"
        template, _ = self.template_manager.get_template_and_variables(template_name)
        if template:
            filename = template.filename
        else:
            filename = os.path.join(self.template_manager.template_dirs[0], template_name)
        file_editor(filename)
        self.template_manager.load_templates()
        self.rebuild_completions()

    def do_template_copy(self, template_names):
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
        template, _ = self.template_manager.get_template_and_variables(old_name)
        if not template:
            return False, template_names, f"{old_name} does not exist"
        old_filepath = template.filename
        new_filepath = os.path.join(os.path.dirname(old_filepath), new_name)
        if os.path.exists(new_filepath):
            return False, template_names, f"{new_name} already exists"
        shutil.copy2(old_filepath, new_filepath)
        self.template_manager.load_templates()
        self.rebuild_completions()
        return True, template_names, f"Copied {old_name} to {new_name}"

    def do_template_delete(self, template_name):
        """
        Deletes an existing template

        Arguments:
            template_name: Required. The name of the template to delete

        Examples:
            {COMMAND} mytemplate.md
        """
        if not template_name:
            return False, template_name, "No template name specified"
        template, _ = self.template_manager.get_template_and_variables(template_name)
        if not template:
            return False, template_name, f"{template_name} does not exist"
        confirmation = input(f"Are you sure you want to delete template {template_name}? [y/N] ").strip()
        if confirmation.lower() in ["yes", "y"]:
            os.remove(template.filename)
            self.template_manager.load_templates()
            self.rebuild_completions()
            return True, template_name, f"Deleted {template_name}"
        else:
            return False, template_name, "Deletion aborted"

    def do_template_run(self, template_name):
        """
        Run a template

        Running a template sends the content of it to the model as your input.

        Arguments:
            template_name: Required. The name of the template.

        Examples:
            {COMMAND} mytemplate.md
        """
        success, template_name, user_message = self.template_manager.ensure_template(template_name)
        if not success:
            return success, template_name, user_message
        _, variables = self.template_manager.get_template_and_variables(template_name)
        substitutions = self.template_manager.process_template_builtin_variables(template_name, variables)
        return self.run_template(template_name, substitutions)

    def do_template_prompt_run(self, template_name):
        """
        Prompt for template variable values, then run

        Prompts for a value for each variable in the template, sustitutes the values
        in the template, and sends the final content to the model as your input.

        Arguments:
            template_name: Required. The name of the template.

        Examples:
            {COMMAND} mytemplate.md
        """
        success, template_name, user_message = self.template_manager.ensure_template(template_name)
        if not success:
            return success, template_name, user_message
        _, variables = self.template_manager.get_template_and_variables(template_name)
        substitutions = self.collect_template_variable_values(template_name, variables)
        return self.run_template(template_name, substitutions)

    def do_template_edit_run(self, template_name):
        """
        Open a template for final editing, then run it

        Open the template in an editor, and upon editor exit, send the final content
        to the model as your input.

        Arguments:
            template_name: Required. The name of the template.

        Examples:
            {COMMAND} mytemplate.md
        """
        success, template_name, user_message = self.template_manager.ensure_template(template_name)
        if not success:
            return success, template_name, user_message
        template, variables = self.template_manager.get_template_and_variables(template_name)
        substitutions = self.template_manager.process_template_builtin_variables(template_name, variables)
        message = template.render(**substitutions)
        return self.do_editor(message)

    def do_template_prompt_edit_run(self, template_name):
        """
        Prompts for a value for each variable in the template, sustitutes the values
        in the template, opens an editor for final edits, and sends the final content
        to the model as your input.

        Arguments:
            template_name: Required. The name of the template.

        Examples:
            {COMMAND} mytemplate.md
        """
        success, template_name, user_message = self.template_manager.ensure_template(template_name)
        if not success:
            return success, template_name, user_message
        template, variables = self.template_manager.get_template_and_variables(template_name)
        substitutions = self.collect_template_variable_values(template_name, variables)
        message = template.render(**substitutions)
        return self.do_editor(message)

    def show_full_config(self):
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
""" % (self.config.get('backend'), self.config.config_dir, self.config.config_profile_dir, self.config.config_file or "None", self.config.data_dir, self.config.data_profile_dir, ", ".join(self.template_manager.template_dirs), self.config.profile, yaml.dump(self.config.get(), default_flow_style=False), str(self.stream), self.logfile and self.logfile.name or "None")
        output += self.backend.get_runtime_config()
        util.print_markdown(output)

    def show_section_config(self, section, section_data):
        config_data = yaml.dump(section_data, default_flow_style=False) if isinstance(section_data, dict) else section_data
        output = """
# Configuration section '%s':

```
%s
```
""" % (section, config_data)
        util.print_markdown(output)

    def do_config(self, arg):
        """
        Show or edit the current configuration

        Examples:
            Show all: {COMMAND}
            Show section: {COMMAND} backend
            Edit config: {COMMAND} edit
        """
        if arg:
            if arg == 'edit':
                file_editor(self.config.config_file)
                self.rebuild_completions()
                return False, None, "Restart to apply changes"
            else:
                section_data = self.config.get(arg)
                if section_data:
                    return self.show_section_config(arg, section_data)
                else:
                    return False, arg, f"Configuration section {arg} does not exist"
        else:
            self.show_full_config()

    def do_exit(self, _):
        """
        Exit the shell

        Examples:
            {COMMAND}
        """
        pass

    def do_quit(self, _):
        """
        Exit the shell

        Examples:
            {COMMAND}
        """
        pass

    def get_command_method(self, command):
        do_command = f"do_{command}"
        method = util.get_class_command_method(self.__class__, do_command)
        if method:
            return method, self
        for plugin in self.plugins.values():
            method = util.get_class_command_method(plugin.__class__, do_command)
            if method:
                return method, plugin
        raise AttributeError(f"{do_command} method not found in any shell class")

    def run_command(self, command, argument):
        command = util.dash_to_underscore(command)
        if command == 'help':
            self.help(argument)
        else:
            if command in self.commands:
                method, obj = self.get_command_method(command)
                try:
                    response = method(obj, argument)
                except Exception as e:
                    print(repr(e))
                    if self.debug:
                        traceback.print_exc()
                else:
                    util.output_response(response)
            else:
                print(f'Unknown command: {command}')

    def cmdloop(self):
        print("")
        util.print_markdown("### %s" % self.intro)
        while True:
            self.set_user_prompt()
            # This extra threading and queuing dance is necessary because
            # the browser backend starts an event loop, and prompt_tookit
            # barfs when it tries to start the application when an event
            # loop is already running.
            # Converting to prompt_async doesn't seem to help, because
            # then Playwright complains that it needs to be run in an async
            # context as well.
            # Happy to accept a better solution to this promblem if it's
            # presented.
            user_input_queue = queue.Queue()
            def prompt_session():
                user_input = None
                try:
                    user_input = self.prompt_session.prompt(
                        self.prompt,
                        completer=self.command_completer,
                    )
                except KeyboardInterrupt:
                    user_input_queue.put(KeyboardInterrupt)
                except EOFError:
                    user_input_queue.put(EOFError)
                if user_input is not None:
                    user_input_queue.put(user_input)
            t = threading.Thread(target=prompt_session)
            t.start()
            user_input = user_input_queue.get()
            if user_input is KeyboardInterrupt:
                continue
            elif user_input is EOFError:
                break
            try:
                command, argument = util.parse_shell_input(user_input)
            except (NoInputError, LegacyCommandLeaderError):
                continue
            except EOFError:
                break
            exec_prompt_pre_result = self.exec_prompt_pre(command, argument)
            if exec_prompt_pre_result:
                util.output_response(exec_prompt_pre_result)
            else:
                self.run_command(command, argument)
        print('GoodBye!')
