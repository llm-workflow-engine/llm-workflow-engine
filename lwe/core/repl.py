import re
import json
import textwrap
import yaml
import os
import traceback
import signal
import frontmatter
import pyperclip

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.filters import Condition

# from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import NestedCompleter, PathCompleter
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.styles import Style
import prompt_toolkit.document as document

import lwe.core.constants as constants
import lwe.core.util as util
from lwe.core.config import Config
from lwe.core.logger import Logger
from lwe.core.error import NoInputError
from lwe.core.editor import file_editor, pipe_editor

# Monkey patch _FIND_WORD_RE in the document module.
# This is needed because the current version of _FIND_WORD_RE
# doesn't allow any special characters in the first word, and we need
# to start commands with a special character.
# It would also be possible to subclass NesteredCompleter and override
# the get_completions() method, but that feels more brittle.
document._FIND_WORD_RE = re.compile(
    r"([a-zA-Z0-9-" + constants.COMMAND_LEADER + r"]+|[^a-zA-Z0-9_\.\s]+)"
)
# I think this 'better' regex should work, but it's not.
# document._FIND_WORD_RE = re.compile(r"(\/|\/?[a-zA-Z0-9_]+|[^a-zA-Z0-9_\s]+)")


class Repl:
    """
    A shell interpreter that serves as a front end to the backend classes
    """

    intro = "Provide a prompt, or type %shelp or ? to list commands." % constants.COMMAND_LEADER
    prompt = "> "
    prompt_prefix = ""
    doc_header = (
        "Documented commands type %shelp [command without %s] (e.g. /help ask) for detailed help"
        % (constants.COMMAND_LEADER, constants.COMMAND_LEADER)
    )

    # our stuff
    prompt_number = 0
    message_map = {}
    logfile = None

    @staticmethod
    def _setup_key_bindings():
        bindings = KeyBindings()

        @bindings.add('c-z', filter=Condition(lambda: hasattr(signal, 'SIGTSTP')))
        def _(event):
            event.app.suspend_to_background()

        return bindings

    def __init__(self, config=None):
        self.initialize_repl(config)
        self.history = self.get_shell_history()
        self.style = self.get_styles()
        self.prompt_session = PromptSession(
            history=self.history,
            # NOTE: Suggestions from history don't seem like a good fit for this REPL,
            # so we don't use it. Leaving it here for reference.
            # auto_suggest=AutoSuggestFromHistory(),
            style=self.style,
            key_bindings=self._setup_key_bindings(),
        )
        self._setup_signal_handlers()

    def initialize_repl(self, config=None):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)

    def reload_repl(self):
        util.print_status_message(True, "Reloading configuration...")
        self.config.load_from_file()
        self.initialize_repl(self.config)
        self.backend.initialize_backend(self.config)
        self.setup()

    def terminate_stream(self, _signal, _frame):
        self.backend.terminate_stream(_signal, _frame)

    def catch_ctrl_c(self, signum, _frame):
        self.log.debug(f"Ctrl-c hit: {signum}")
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
        self.all_commands = self.dashed_commands + ["help"]
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
        config_args = sorted(
            ["edit", "files", "profile", "runtime"]
            + list(self.config.get().keys())
            + self.config.properties
        )
        commands_with_leader[util.command_with_leader("config")] = util.list_to_completion_hash(
            config_args
        )
        commands_with_leader[util.command_with_leader("help")] = util.list_to_completion_hash(
            self.dashed_commands
        )
        for command in ["file", "log"]:
            commands_with_leader[util.command_with_leader(command)] = PathCompleter()
        template_completions = util.list_to_completion_hash(self.backend.template_manager.templates)
        commands_with_leader[util.command_with_leader("template")] = {
            c: template_completions for c in self.get_command_actions("template", dashed=True)
        }
        commands_with_leader[util.command_with_leader("plugin")] = {
            "reload": util.list_to_completion_hash(self.backend.plugin_manager.plugin_list)
        }
        self.base_shell_completions = commands_with_leader

    def rebuild_completions(self):
        self.set_base_shell_completions()
        completions = util.merge_dicts(
            self.base_shell_completions, self.get_custom_shell_completions()
        )
        completions = self.get_plugin_shell_completions(completions)
        self.command_completer = NestedCompleter.from_nested_dict(completions)

    def get_shell_history(self):
        history_file = self.config.get("shell.history_file")
        if history_file:
            return FileHistory(history_file)

    def get_styles(self):
        style = Style.from_dict(
            {
                "prompt": "bold",
                "completion-menu.completion": "bg:#008888 #ffffff",
                "completion-menu.completion.current": "bg:#00aaaa #000000",
                "scrollbar.background": "bg:#88aaaa",
                "scrollbar.button": "bg:#222222",
            }
        )
        return style

    def run_template(self, template_name, substitutions=None):
        success, response, user_message = self.backend.run_template_setup(
            template_name, substitutions
        )
        if not success:
            return success, response, user_message
        message, overrides = response
        print("")
        print(message)
        self.log.info("Running template")
        response = self.default(message, **overrides)
        return response

    def edit_run_template(self, template_content, suffix="md"):
        template_name, filepath = self.backend.template_manager.make_temp_template(
            template_content, suffix
        )
        file_editor(filepath)
        response = self.run_template(template_name)
        self.backend.template_manager.remove_temp_template(template_name)
        return response

    def collect_template_variable_values(self, template_name, variables=None):
        variables = variables or []
        substitutions = {}
        builtin_variables = self.backend.template_manager.template_builtin_variables()
        user_variables = list(set([v for v in variables if v not in builtin_variables]))
        if user_variables:
            self.command_template(template_name)
            util.print_markdown("##### Enter variables:\n")
            self.log.debug(f"Collecting variable values for: {template_name}")
            for variable in user_variables:
                substitutions[variable] = input(f"    {variable}: ").strip()
                self.log.debug(
                    f"Collected variable {variable} for template {template_name}: {substitutions[variable]}"
                )
        substitutions = util.merge_dicts(
            substitutions,
            self.backend.template_manager.process_template_builtin_variables(
                template_name, variables
            ),
        )
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
                doc = doc.replace(
                    "{COMMAND}",
                    "%s%s" % (constants.COMMAND_LEADER, util.underscore_to_dash(command)),
                )
                for sub in constants.HELP_TOKEN_VARIABLE_SUBSTITUTIONS:
                    try:
                        const_value = getattr(constants, sub)
                    except AttributeError as err:
                        raise AttributeError(
                            f"{sub!r} in HELP_TOKEN_VARIABLE_SUBSTITUTIONS is not a valid constant"
                        ) from err
                    doc = doc.replace("{%s}" % sub, str(const_value))
                return textwrap.dedent(doc)

    def help_commands(self):
        print("")
        util.print_markdown(f"#### {self.doc_header}")
        print("")
        for command in self.dashed_commands:
            print(self.get_command_help_brief(command))
        print("")

    def help(self, command=""):
        if command:
            help_doc = self.get_command_help(command)
            if help_doc:
                print(help_doc)
            else:
                print(
                    "\nNo help for '%s'\n\nAvailable commands: %s"
                    % (command, ", ".join(self.dashed_commands))
                )
        else:
            self.help_commands()

    def _set_prompt(self, prefix=""):
        self.prompt = f"{self.prompt_prefix}{self.prompt_number}> "

    def _set_prompt_prefix(self, prefix=""):
        self.prompt_prefix = prefix

    def _update_message_map(self):
        self.prompt_number += 1
        self.message_map[self.prompt_number] = (self.backend.conversation_id,)
        self._set_prompt()

    def build_shell_user_prefix(self):
        return ""

    def set_user_prompt(self, user=None):
        prefix = self.build_shell_user_prefix()
        self._set_prompt_prefix(prefix)
        self._set_prompt()

    def configure_plugins(self):
        self.plugin_manager = self.backend.plugin_manager
        self.plugins = self.plugin_manager.get_plugins()
        for plugin in self.plugins.values():
            plugin.set_shell(self)

    def configure_backend(self):
        raise NotImplementedError

    def launch_backend(self, interactive=True):
        raise NotImplementedError

    def setup(self):
        self.configure_backend()
        self.configure_plugins()
        self.stream = self.config.get("shell.streaming")
        self.backend.template_manager.load_templates()
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
        success, _, message = self.backend.set_title(title, conversation["id"])
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
                util.print_status_message(
                    False, f"Failed to deleted conversation: {label}, {message}"
                )

    def _delete_current_conversation(self):
        util.print_markdown("* Deleting current conversation")
        success, conversation, message = self.backend.delete_conversation()
        if success:
            util.print_status_message(True, "Deleted current conversation")
            self.command_new(None)
        else:
            util.print_status_message(False, "Failed to delete current conversation")

    def dispatch_command_action(self, command, args):
        try:
            action, *action_args = args.split()
        except ValueError:
            return False, None, f"Action required for {constants.COMMAND_LEADER}{command} command"
        try:
            method, klass = self.get_command_action_method(command, action)
        except AttributeError:
            return (
                False,
                None,
                f"Invalid action {action} for {constants.COMMAND_LEADER}{command} command",
            )
        action_args.insert(0, klass)
        return method(*action_args)

    def get_command_actions(self, command, dashed=False):
        command_actions = util.introspect_command_actions(self.__class__, command)
        for plugin in self.plugins.values():
            plugin_command_actions = util.introspect_command_actions(plugin.__class__, command)
            command_actions.extend(plugin_command_actions)
        if dashed:
            command_actions = list(map(util.underscore_to_dash, command_actions))
        return command_actions

    def command_stream(self, _):
        """
        Toggle streaming mode

        Streaming mode: streams the raw response (no markdown rendering)
        Non-streaming mode: Returns full response at completion (markdown rendering supported).

        Examples:
            {COMMAND}
        """
        self.stream = not self.stream
        util.print_markdown(f"* Streaming mode is now {'enabled' if self.stream else 'disabled'}.")

    def command_new(self, _):
        """
        Start a new conversation

        Examples:
            {COMMAND}
        """
        self.backend.new_conversation()
        util.print_markdown("* New conversation started.")
        self._update_message_map()

    def command_delete(self, arg):
        """
        Delete one or more conversations

        Can delete by conversation ID, history ID, or current conversation.

        Arguments:
            history_id : The history ID

        Arguments can be mixed and matched as in the examples below.

        Examples:
            Current conversation: {COMMAND}
            Delete one: {COMMAND} 3
            Multiple IDs: {COMMAND} 1,5
            Ranges: {COMMAND} 1-5
            Complex: {COMMAND} 1,3-5
        """
        if arg:
            result = util.parse_conversation_ids(arg)
            if isinstance(result, list):
                success, conversations, message = self._fetch_history()
                if success:
                    history_list = list(conversations.values())
                    for item in result:
                        if isinstance(item, str) and len(item) == 36:
                            self._delete_conversation(item)
                        else:
                            if item <= len(history_list):
                                conversation = history_list[item - 1]
                                self._delete_conversation(conversation["id"], conversation["title"])
                            else:
                                util.print_status_message(
                                    False, f"Cannont delete history item {item}, does not exist"
                                )
                else:
                    return success, conversations, message
            else:
                return False, None, result
        else:
            self._delete_current_conversation()

    def command_copy(self, _):
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

    def command_history(self, arg):
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
            args = arg.split(" ")
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
            util.print_markdown(
                "## Recent history:\n\n%s"
                % "\n".join(
                    [
                        "1. %s: %s (%s)%s"
                        % (
                            h["created_time"].strftime("%Y-%m-%d %H:%M"),
                            h["title"] or constants.NO_TITLE_TEXT,
                            h["id"],
                            (
                                f" {constants.ACTIVE_ITEM_INDICATOR}"
                                if h["id"] == self.backend.conversation_id
                                else ""
                            ),
                        )
                        for h in history_list
                    ]
                )
            )
        else:
            return success, history, message

    # TODO: Decide if reviving this is a good idea.
    # def command_nav(self, arg):
    #     """
    #     Navigate to a past point in the conversation

    #     Arguments:
    #         id: prompt ID

    #     Examples:
    #         {COMMAND} 2
    #     """

    #     try:
    #         msg_id = int(arg)
    #     except Exception:
    #         util.print_markdown("The argument to nav must be an integer.")
    #         return

    #     if msg_id == self.prompt_number:
    #         util.print_markdown("You are already using prompt {msg_id}.")
    #         return

    #     if msg_id not in self.message_map:
    #         util.print_markdown(
    #             "The argument to `nav` contained an unknown prompt number."
    #         )
    #         return
    #     elif self.message_map[msg_id][0] is None:
    #         util.print_markdown(
    #             f"Cannot navigate to prompt number {msg_id}, no conversation present, try next prompt."
    #         )
    #         return

    #     (
    #         self.backend.conversation_id,
    #     ) = self.message_map[msg_id]
    #     self._update_message_map()
    #     util.print_markdown(
    #         f"* Prompt {self.prompt_number} will use the context from prompt {arg}."
    #     )

    def command_title(self, arg):
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
                kwargs["limit"] = id
            success, conversations, message = self._fetch_history(**kwargs)
            if success:
                history_list = list(conversations.values())
                conversation = None
                if id:
                    if id <= len(history_list):
                        conversation = history_list[id - 1]
                    else:
                        return (
                            False,
                            conversations,
                            "Cannot set title on history item %d, does not exist" % id,
                        )
                    new_title = input(
                        "Enter new title for '%s': " % conversation["title"]
                        or constants.NO_TITLE_TEXT
                    )
                else:
                    if self.backend.conversation_id:
                        if self.backend.conversation_id in conversations:
                            conversation = conversations[self.backend.conversation_id]
                        else:
                            success, conversation_data, message = self.backend.get_conversation(
                                self.backend.conversation_id
                            )
                            if not success:
                                return success, conversation_data, message
                            conversation = conversation_data["conversation"]
                        new_title = arg
                    else:
                        return (
                            False,
                            None,
                            "Current conversation has no title, you must send information first",
                        )
                conversation["title"] = new_title
                return self._set_title(new_title, conversation)
            else:
                return success, conversations, message
        else:
            if self.backend.conversation_id:
                success, conversation_data, message = self.backend.get_conversation()
                if success:
                    util.print_markdown(
                        "* Title: %s" % conversation_data["conversation"]["title"]
                        or constants.NO_TITLE_TEXT
                    )
                else:
                    return success, conversation_data, message
            else:
                return (
                    False,
                    None,
                    "Current conversation has no title, you must send information first",
                )

    def command_chat(self, arg):
        """
        Retrieve chat content

        Arguments:
            history_id: The history ID
            With no arguments, show content of the current conversation.

        Examples:
            Current conversation: {COMMAND}
            Older conversation: {COMMAND} 2
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
                    kwargs["limit"] = id
                success, conversations, message = self._fetch_history(**kwargs)
                if success:
                    history_list = list(conversations.values())
                    if id <= len(history_list):
                        conversation = history_list[id - 1]
                        title = conversation["title"] or constants.NO_TITLE_TEXT
                    else:
                        return (
                            False,
                            conversations,
                            f"Cannot retrieve chat content on history item {id}, does not exist",
                        )
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
                    util.print_markdown(f"## {title}")
                conversation_parts = util.conversation_from_messages(messages)
                for part in conversation_parts:
                    print("\n")
                    style = "bold red3" if part["role"] == "user" else "bold green3"
                    util.print_markdown(part["display_role"], style=style)
                    if type(part["message"]) is dict or type(part["message"]) is list:
                        message = f"```json\n{json.dumps(part['message'], indent=2)}\n```"
                    else:
                        message = part["message"]
                    util.print_markdown(message)
            else:
                return False, conversation_data, "Could not load chat content"
        else:
            return success, conversation_data, message

    def command_switch(self, arg):
        """
        Switch to chat

        Arguments:
            history_id: The history ID of the conversation

        Examples:
            {COMMAND} 2
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
                    kwargs["limit"] = id
                success, conversations, message = self._fetch_history(**kwargs)
                if success:
                    history_list = list(conversations.values())
                    if id <= len(history_list):
                        conversation = history_list[id - 1]
                        title = conversation["title"] or constants.NO_TITLE_TEXT
                    else:
                        return (
                            False,
                            conversations,
                            f"Cannot retrieve chat content on history item {id}, does not exist",
                        )
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
                self.backend.switch_to_conversation(conversation_id)
                self._update_message_map()
                if title:
                    util.print_markdown(f"### Switched to: {title}")
            else:
                return False, conversation_data, "Could not switch to chat"
        else:
            return success, conversation_data, message

    def command_ask(self, input):
        """
        Ask a question

        It is purely optional.

        Examples:
            {COMMAND} what is 6+6 (is the same as 'what is 6+6')
        """
        return self.default(input)

    def default(self, input, request_overrides=None):
        # TODO: This signal is recognized on Windows, and calls the callback, but the entire
        # process is still killed.
        signal.signal(signal.SIGINT, self.catch_ctrl_c)
        if not input:
            return

        request_overrides = request_overrides or {}
        if self.stream:
            request_overrides["print_stream"] = True
            print("")
            success, response, user_message = self.backend.ask_stream(
                input, request_overrides=request_overrides
            )
            print("\n")
            if not success:
                return success, response, user_message
        else:
            success, response, user_message = self.backend.ask(
                input, request_overrides=request_overrides
            )
            if success:
                print("")
                util.print_markdown(response)
            else:
                return success, response, user_message

        self._update_message_map()

    def command_read(self, _):
        """
        Begin reading multi-line input

        Allows for entering more complex multi-line input prior to sending it.

        Examples:
            {COMMAND}
        """
        ctrl_sequence = "^z" if util.is_windows else "^d"
        util.print_markdown(
            f"* Reading prompt, hit {ctrl_sequence} when done, or write line with /end."
        )

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

    def command_editor(self, args):
        """
        Open an editor for entering a command

        When the editor is closed, the content is sent.

        Arguments:
            default_text: The default text to open the editor with

        Examples:
            {COMMAND}
            {COMMAND} some text to start with
        """
        output = pipe_editor(args, suffix="md")
        print(output)
        self.default(output)

    def command_file(self, arg):
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
            util.print_markdown(f"Failed to read file {arg!r}")
            return
        self.default(fileprompt)

    def command_log(self, arg):
        """
        Enable/disable logging to a file

        Arguments:
            file_name: The name of the file to write to

        Examples:
            Log to file: {COMMAND} mylog.txt
            Disable logging: {COMMAND}
        """
        if arg:
            if self.backend.open_log(arg):
                util.print_markdown(f"* Logging enabled, appending to {arg!r}.")
            else:
                util.print_markdown(f"Failed to open log file {arg!r}.")
        else:
            self.backend.close_log()
            util.print_markdown("* Logging is now disabled.")

    # TODO: Decide if this should be revived.
    # def command_context(self, arg):
    #     """
    #     Load an old context from the log

    #     Arguments:
    #         context_string: a context string from logs

    #     Examples:
    #         {COMMAND} 67d1a04b-4cde-481e-843f-16fdb8fd3366:0244082e-8253-43f3-a00a-e2a82a33cba6
    #     """
    #     try:
    #         conversation_id = arg
    #         assert conversation_id == "None" or len(conversation_id) == 36
    #     except Exception:
    #         util.print_markdown("Invalid parameter to `context`.")
    #         return
    #     util.print_markdown("* Loaded specified context.")
    #     self.backend.conversation_id = (
    #         conversation_id if conversation_id != "None" else None
    #     )
    #     self._update_message_map()

    def command_model(self, arg):
        """
        View or set attributes on the current LLM model

        Arguments:
            path: The attribute path to view or set
            value: The value to set the attribute to
            With no arguments, view current set model attributes

        Examples:
            {COMMAND}
            {COMMAND} temperature
            {COMMAND} temperature 1.1
        """
        if arg:
            try:
                path, value, *rest = arg.split()
                if rest:
                    return False, arg, "Too many parameters, should be 'path value'"
                if path == self.backend.provider.model_property_name:
                    success, value, user_message = self.backend.set_model(value)
                else:
                    success, value, user_message = self.backend.provider.set_customization_value(
                        path, value
                    )
                if success:
                    model_name = value.get(self.backend.provider.model_property_name, "unknown")
                    self.backend.model = model_name
                return success, value, user_message
            except ValueError:
                success, value, user_message = self.backend.provider.get_customization_value(arg)
                if success:
                    if isinstance(value, dict):
                        util.print_markdown(
                            "\n```yaml\n%s\n```" % yaml.dump(value, default_flow_style=False)
                        )
                    else:
                        util.print_markdown(f"* {arg} = {value}")
                else:
                    return success, value, user_message
        else:
            customizations = self.backend.provider.get_customizations()
            model_name = customizations.pop(self.backend.provider.model_property_name, "unknown")
            customizations_data = (
                "\n\n```yaml\n%s\n```" % yaml.dump(customizations, default_flow_style=False)
                if customizations
                else ""
            )
            util.print_markdown(
                "## Provider: %s, model: %s%s"
                % (self.backend.provider.display_name, model_name, customizations_data)
            )

    def command_templates(self, arg):
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
        # Clean out temporary templates.
        self.backend.template_manager.make_temp_template_dir()
        self.backend.template_manager.load_templates()
        self.rebuild_completions()
        templates = []
        for template_name in self.backend.template_manager.templates:
            content = f"* **{template_name}**"
            template, _ = self.backend.template_manager.get_template_and_variables(template_name)
            try:
                source = frontmatter.load(template.filename)
            except yaml.parser.ParserError:
                util.print_status_message(False, f"Failed to parse template: {template_name}")
                continue
            if "description" in source.metadata:
                content += f": *{source.metadata['description']}*"
            if not arg or arg.lower() in content.lower():
                templates.append(content)
        util.print_markdown("## Templates:\n\n%s" % "\n".join(sorted(templates)))

    def command_template(self, args):
        """
        Run actions on available templates

        Templates are pre-configured text content that can be customized before sending a message to the model.

        'Running' a template sends its content (after variable substitutions) to the model as your input.

        Available actions:
            * copy: Copy a template
            * delete: Delete a template
            * edit: Open or create a template for editing
            * edit-run: Open the template in an editor, then run it on editor save and close.
            * prompt-edit-run: Collect values for template variables, then open in an editor, then run it on editor save and close
            * prompt-run: Collect values for template variables, then run it
            * run: Run a template
            * show: Show a template

        Arguments:
            template_name: Required. The name of the template.

            For copy, a new template name is also required.

        Examples:
            * /template copy mytemplate.md mytemplate_copy.md
            * /template delete mytemplate.md
            * /template edit mytemplate.md
            * /template edit-run mytemplate.md
            * /template prompt-edit-run mytemplate.md
            * /template prompt-run mytemplate.md
            * /template run mytemplate.md
            * /template show mytemplate.md
        """
        return self.dispatch_command_action("template", args)

    def action_template_show(self, template_name):
        """
        Display a template.

        :param template_name: The name of the template.
        :type template_name: str
        """
        success, source, user_message = self.backend.template_manager.get_template_source(
            template_name
        )
        if not success:
            return success, source, user_message
        util.print_markdown(f"\n## Template {template_name!r}")
        if source.metadata:
            util.print_markdown(
                "\n```yaml\n%s\n```" % yaml.dump(source.metadata, default_flow_style=False)
            )
        util.print_markdown(f"\n\n{source.content}")

    def action_template_edit(self, template_name):
        """
        Create a new template, or edit an existing template.

        :param template_name: The name of the template.
        :type template_name: str
        """
        (
            success,
            filepath,
            user_message,
        ) = self.backend.template_manager.get_template_editable_filepath(template_name)
        if not success:
            return success, filepath, user_message
        file_editor(filepath)
        self.backend.template_manager.load_templates()
        self.rebuild_completions()

    def action_template_copy(self, *template_names):
        """
        Copies an existing template and saves it as a new template.

        :param template_names: The names of the old and new templates.
        :type template_names: tuple
        :return: Success status, new file path, and user message.
        :rtype: tuple
        """
        try:
            old_name, new_name = template_names
        except ValueError:
            return False, template_names, "Old and new template name required"

        success, new_filepath, user_message = self.backend.template_manager.copy_template(
            old_name, new_name
        )
        if not success:
            return success, new_filepath, user_message
        self.rebuild_completions()
        return True, new_filepath, f"Copied {old_name} to {new_filepath}"

    def action_template_delete(self, template_name):
        """
        Deletes an existing template.

        :param template_name: The name of the template to delete.
        :type template_name: str
        """
        success, filename, user_message = self.backend.template_manager.template_can_delete(
            template_name
        )
        if not success:
            return success, filename, user_message
        confirmation = input(
            f"Are you sure you want to delete template {template_name}? [y/N] "
        ).strip()
        if confirmation.lower() in ["yes", "y"]:
            return self.backend.template_manager.template_delete(filename)
        else:
            return False, template_name, "Deletion aborted"

    def action_template_run(self, template_name):
        """
        Run a template.

        :param template_name: The name of the template.
        :type template_name: str
        """
        (
            success,
            response,
            user_message,
        ) = self.backend.template_manager.get_template_variables_substitutions(template_name)
        if not success:
            return success, template_name, user_message
        _template, variables, substitutions = response
        return self.run_template(template_name, substitutions)

    def action_template_prompt_run(self, template_name):
        """
        Prompt for template variable values, then run.

        :param template_name: The name of the template.
        :type template_name: str
        """
        response = self.action_template_show(template_name)
        if response:
            return response
        (
            success,
            response,
            user_message,
        ) = self.backend.template_manager.get_template_variables_substitutions(template_name)
        if not success:
            return success, template_name, user_message
        _template, variables, _substitutions = response
        substitutions = self.collect_template_variable_values(template_name, variables)
        return self.run_template(template_name, substitutions)

    def action_template_edit_run(self, template_name):
        """
        Open a template for final editing, then run it.

        :param template_name: The name of the template.
        :type template_name: str
        """
        success, template_content, user_message = self.backend.template_manager.get_raw_template(
            template_name
        )
        if not success:
            return success, template_name, user_message
        return self.edit_run_template(template_content)

    def action_template_prompt_edit_run(self, template_name):
        """
        Prompts for a value for each variable in the template, sustitutes the values
        in the template, opens an editor for final edits, and sends the final content
        to the model as your input.

        :param template_name: The name of the template.
        :type template_name: str
        """
        response = self.action_template_show(template_name)
        if response:
            return response
        (
            success,
            response,
            user_message,
        ) = self.backend.template_manager.get_template_variables_substitutions(template_name)
        if not success:
            return success, template_name, user_message
        template, variables, _substitutions = response
        substitutions = self.collect_template_variable_values(template_name, variables)
        template_content = template.render(**substitutions)
        return self.edit_run_template(template_content)

    def command_plugin(self, args):
        """
        Perform operations on plugins.

        Arguments:
            action: The action to perform. One of: reload
            target: The target for the action.

        Examples:
            {COMMAND} reload echo
            {COMMAND} reload provider_chat_openai
        """
        return self.dispatch_command_action("plugin", args)

    def action_plugin_reload(self, plugin_name):
        if plugin_name not in self.backend.plugin_manager.plugins:
            return (
                False,
                plugin_name,
                f"Plugin {plugin_name} not found in list of installed plugins",
            )
        plugin_instance = self.backend.plugin_manager.plugins[plugin_name]
        self.backend.cache_manager.cache_delete(plugin_instance.plugin_cache_filename)
        result = self.backend.reload_plugin(plugin_name)
        self.rebuild_completions()
        return result

    def command_plugins(self, arg):
        """
        List installed plugins

        Plugins are enabled by adding their name to the list of enabled plugins
        in the profile configuration.

        Arguments:
            filter_string: Optional. String to filter plugins by. Name and description are matched.

        Examples:
            {COMMAND}
            {COMMAND} shell
        """
        plugin_list = []
        provider_plugin_list = []
        for plugin in self.plugins.values():
            content = f"* {plugin.name}"
            if plugin.description:
                content += f": *{plugin.description}*"
            if not arg or arg.lower() in content.lower():
                if plugin.plugin_type == "provider":
                    provider_plugin_list.append(content)
                else:
                    plugin_list.append(content)
        plugin_list.sort()
        provider_plugin_list.sort()
        util.print_markdown("## Enabled command plugins:\n\n%s" % "\n".join(plugin_list))
        util.print_markdown("## Enabled provider plugins:\n\n%s" % "\n".join(provider_plugin_list))

    def show_backend_config(self):
        output = """
# Backend configuration: %s
""" % (
            self.backend.name,
        )
        util.print_markdown(output)

    def show_files_config(self):
        output = """
# File configuration

* **Config dir:** %s
* **Config profile dir:** %s
* **Config file:** %s
* **Data dir:** %s
* **Data profile dir:** %s
* **Database:** %s
* **Cache dirs:**
%s
* **Template dirs:**
%s
* **Preset dirs:**
%s
* **Workflow dirs:**
%s
* **Tool dirs:**
%s
""" % (
            self.config.config_dir,
            self.config.config_profile_dir,
            self.config.config_file or "None",
            self.config.data_dir,
            self.config.data_profile_dir,
            self.config.get("database"),
            util.list_to_markdown_list(self.backend.cache_manager.cache_dirs),
            util.list_to_markdown_list(self.backend.template_manager.user_template_dirs),
            util.list_to_markdown_list(self.backend.preset_manager.user_preset_dirs),
            (
                util.list_to_markdown_list(self.backend.workflow_manager.user_workflow_dirs)
                if getattr(self.backend, "workflow_manager", None)
                else ""
            ),
            (
                util.list_to_markdown_list(self.backend.tool_manager.user_tool_dirs)
                if getattr(self.backend, "tool_manager", None)
                else ""
            ),
        )
        util.print_markdown(output)

    def show_profile_config(self):
        output = """
# Profile '%s' configuration:

```yaml
%s
```
""" % (
            self.config.profile,
            yaml.dump(self.config.get(), default_flow_style=False),
        )
        util.print_markdown(output)

    def show_runtime_config(self):
        output = """
# Runtime configuration

* Streaming: %s
* Logging to: %s
""" % (
            str(self.stream),
            self.backend.logfile and self.backend.logfile.name or "None",
        )
        output += self.backend.get_runtime_config()
        util.print_markdown(output)

    def show_section_config(self, section, section_data):
        config_data = (
            yaml.dump(section_data, default_flow_style=False)
            if isinstance(section_data, dict)
            else section_data
        )
        output = """
# Configuration section '%s':

```yaml
%s
```
""" % (
            section,
            config_data,
        )
        util.print_markdown(output)

    def show_full_config(self):
        self.show_backend_config()
        self.show_files_config()
        self.show_profile_config()
        self.show_runtime_config()

    def command_config(self, arg):
        """
        Show or edit the current configuration

        Examples:
            Show all: {COMMAND}
            Edit config: {COMMAND} edit
            Show files config: {COMMAND} files
            Show profile config: {COMMAND} profile
            Show runtime config: {COMMAND} runtime
            Show section: {COMMAND} debug
        """
        if arg:
            if arg in self.config.properties:
                property = getattr(self.config, arg, None)
                print(property)
            if arg == "edit":
                file_editor(self.config.config_file)
                self.reload_repl()
                return True, None, "Reloaded configuration"
            elif arg == "files":
                return self.show_files_config()
            elif arg == "profile":
                return self.show_profile_config()
            elif arg == "runtime":
                return self.show_runtime_config()
            else:
                section_data = self.config.get(arg)
                if section_data:
                    return self.show_section_config(arg, section_data)
                else:
                    return False, arg, f"Configuration section {arg} does not exist"
        else:
            self.show_full_config()

    def command_exit(self, _):
        """
        Exit the shell

        Examples:
            {COMMAND}
        """
        pass

    def command_quit(self, _):
        """
        Exit the shell

        Examples:
            {COMMAND}
        """
        pass

    def get_command_method(self, command):
        return self.get_shell_method(f"command_{command}")

    def get_command_action_method(self, command, action):
        return self.get_shell_method(util.dash_to_underscore(f"action_{command}_{action}"))

    def get_shell_method(self, method_string):
        method = util.get_class_method(self.__class__, method_string)
        if method:
            return method, self
        for plugin in self.plugins.values():
            method = util.get_class_method(plugin.__class__, method_string)
            if method:
                return method, plugin
        raise AttributeError(f"{method_string} method not found in any shell class")

    def run_command_get_response(self, command, argument):
        command = util.dash_to_underscore(command)
        if command in self.commands:
            method, obj = self.get_command_method(command)
            try:
                response = method(obj, argument)
                return True, response
            except Exception as e:
                return False, e
        return False, f"Unknown command: {command}"

    def run_command(self, command, argument):
        if command == "help":
            self.help(argument)
        else:
            success, response = self.run_command_get_response(command, argument)
            if success:
                util.output_response(response)
            else:
                print(repr(response))
                if self.config.debug:
                    traceback.print_exc()

    def cmdloop(self):
        print("")
        util.print_markdown("### %s" % self.intro)
        while True:
            self.set_user_prompt()
            try:
                user_input = self.prompt_session.prompt(
                    self.prompt,
                    completer=self.command_completer,
                    complete_style=CompleteStyle.MULTI_COLUMN,
                    reserve_space_for_menu=3,
                )
            except (KeyboardInterrupt, EOFError):
                break
            try:
                command, argument = util.parse_shell_input(user_input)
            except NoInputError:
                continue
            except EOFError:
                break
            exec_prompt_pre_result = self.exec_prompt_pre(command, argument)
            if exec_prompt_pre_result:
                util.output_response(exec_prompt_pre_result)
            else:
                self.run_command(command, argument)
        print("GoodBye!")
