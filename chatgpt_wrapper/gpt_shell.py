import re
import textwrap
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
# from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
import prompt_toolkit.document as document

import os
import platform
import sys
import datetime
import subprocess

from rich.console import Console
from rich.markdown import Markdown

console = Console()

is_windows = platform.system() == "Windows"

COMMAND_LEADER = '/'
LEGACY_COMMAND_LEADER = '!'
DEFAULT_COMMAND = 'ask'
COMMAND_HISTORY_FILE = '/tmp/repl_history.log'

# Monkey patch _FIND_WORD_RE in the document module.
# This is needed because the current version of _FIND_WORD_RE
# doesn't allow any special characters in the first word, and we need
# to start commands with a special character.
# It would also be possible to subclass NesteredCompleter and override
# the get_completions() method, but that feels more brittle.
document._FIND_WORD_RE = re.compile(r"([a-zA-Z0-9_" + COMMAND_LEADER + r"]+|[^a-zA-Z0-9_\s]+)")
# I think this 'better' regex should work, but it's not.
# document._FIND_WORD_RE = re.compile(r"(\/|\/?[a-zA-Z0-9_]+|[^a-zA-Z0-9_\s]+)")

DEFAULT_HISTORY_LIMIT = 20

class GPTShell():
    """
    A shell interpreter that serves as a front end to the ChatGPT class
    """

    intro = "Provide a prompt for ChatGPT, or type %shelp or ? to list commands." % COMMAND_LEADER
    prompt = "> "
    doc_header = "Documented commands (type %shelp [command without leading %s]):" % (COMMAND_LEADER, COMMAND_LEADER)

    # our stuff
    prompt_number = 0
    chatgpt = None
    message_map = {}
    stream = False
    logfile = None

    def __init__(self):
        self.commands = self.configure_commands()
        self.command_completer = self.get_command_completer()
        self.history = self.get_history()
        self.key_bindings = self.get_key_bindings()
        self.style = self.get_styles()
        self.prompt_session = PromptSession(
            history=self.history,
            #auto_suggest=AutoSuggestFromHistory(),
            completer=self.command_completer,
            key_bindings=self.key_bindings,
            style=self.style
        )

    def configure_commands(self):
        commands = [method[3:] for method in dir(__class__) if callable(getattr(__class__, method)) and method.startswith("do_")]
        return commands

    def get_command_completer(self):
        commands_with_leader = {"%s%s" % (COMMAND_LEADER, key): None for key in self.commands}
        commands_with_leader["%shelp" % COMMAND_LEADER] = {key: None for key in self.commands}
        completer = NestedCompleter.from_nested_dict(commands_with_leader)
        return completer

    def get_history(self):
        return FileHistory(COMMAND_HISTORY_FILE)

    def get_key_bindings(self):
        key_bindings = KeyBindings()
        @key_bindings.add('c-x')
        def _(event):
            event.cli.current_buffer.insert_text('!command1')
        return key_bindings

    def get_styles(self):
        style = Style.from_dict({
            'completion-menu.completion': 'bg:#008888 #ffffff',
            'completion-menu.completion.current': 'bg:#00aaaa #000000',
            'scrollbar.background': 'bg:#88aaaa',
            'scrollbar.button': 'bg:#222222',
        })
        return style

    def legacy_command_leader_warning(self, command):
        print("\nWarning: The legacy command leader '%s' has been removed.\n"
              "Use the new command leader '%s' instead, e.g. %s%s\n" % (
                  LEGACY_COMMAND_LEADER, COMMAND_LEADER, COMMAND_LEADER, command))

    def get_command_help_brief(self, command):
        help_doc = self.get_command_help(command)
        if help_doc:
            first_line = next(filter(lambda x: x.strip(), help_doc.splitlines()), "")
            help_brief = "    %s%s: %s" % (COMMAND_LEADER, command, first_line)
            return help_brief

    def get_command_help(self, command):
        if command in self.commands:
            method = getattr(__class__, f"do_{command}")
            help_text = method.__doc__.replace("{leader}", COMMAND_LEADER)
            return textwrap.dedent(help_text)

    def help_commands(self):
        print("")
        self._print_markdown(f"#### {self.doc_header}")
        print("")
        for command in self.commands:
            print(self.get_command_help_brief(command))
        print("")

    def help(self, command=''):
        if command:
            help_doc = self.get_command_help(command)
            if help_doc:
                print(help_doc)
            else:
                print("\nNo help for '%s'\n\nAvailable commands: %s" % (command, ", ".join(self.commands)))
        else:
            self.help_commands()

    def _set_args(self, args):
        self.stream = args.stream
        if args.log is not None:
            if not self._open_log(args.log):
                sys.exit(0)

    def _set_chatgpt(self, chatgpt):
        self.chatgpt = chatgpt
        self._update_message_map()

    def _set_prompt(self):
        self.prompt = f"{self.prompt_number}> "

    def _update_message_map(self):
        self.prompt_number += 1
        self.message_map[self.prompt_number] = (
            self.chatgpt.conversation_id,
            self.chatgpt.parent_message_id,
        )
        self._set_prompt()

    def _print_markdown(self, output):
        console.print(Markdown(output))
        print("")

    def _write_log(self, prompt, response):
        if self.logfile is not None:
            self.logfile.write(f"{self.prompt_number}> {prompt}\n\n{response}\n\n")
            self._write_log_context()

    def _write_log_context(self):
        if self.logfile is not None:
            self.logfile.write(
                f"## context {self.chatgpt.conversation_id}:{self.chatgpt.parent_message_id}\n"
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
                    sub_items = [int(item) for item in sub_items if int(item) >= 1 and int(item) <= DEFAULT_HISTORY_LIMIT]
                except ValueError:
                    return "Error: Invalid range, must be two ordered history numbers separated by '-', e.g. '1-10'."
                if len(sub_items) == 1:
                    final_list.extend(sub_items)
                elif len(sub_items) == 2 and sub_items[0] < sub_items[1]:
                    final_list.extend(list(range(sub_items[0], sub_items[1] + 1)))
                else:
                    return "Error: Invalid range, must be two ordered history numbers separated by '-', e.g. '1-10'."
        return list(set(final_list))

    def _conversation_from_messages(self, messages):
        message_parts = []
        for message in messages:
            if 'content' in message:
                message_parts.append("**%s**:" % message['author']['role'].capitalize())
                message_parts.extend(message['content']['parts'])
        content = "\n\n".join(message_parts)
        return content

    def _fetch_history(self, limit=DEFAULT_HISTORY_LIMIT, offset=0):
        self._print_markdown("* Fetching conversation history...")
        history = self.chatgpt.get_history(limit=limit, offset=offset)
        return history

    def _set_title(self, title, conversation_id=None):
        self._print_markdown("* Setting title...")
        if self.chatgpt.set_title(title, conversation_id):
            self._print_markdown("* Title set to: %s" % title)

    def _delete_conversation(self, id, label=None):
        if id == self.chatgpt.conversation_id:
            self._delete_current_conversation()
        else:
            label = label or id
            self._print_markdown("* Deleting conversation: %s" % label)
            if self.chatgpt.delete_conversation(id):
                self._print_markdown("* Deleted conversation: %s" % label)

    def _delete_current_conversation(self):
        self._print_markdown("* Deleting current conversation")
        if self.chatgpt.delete_conversation():
            self._print_markdown("* Deleted current conversation")
            self.do_new(None)

    def do_stream(self, _):
        """
        Toggle streaming mode

        Streaming mode: streams the raw response from ChatGPT (no markdown rendering)
        Non-streaming mode: Returns full response at completion (markdown rendering supported).

        Examples:
            {leader}stream
        """
        self.stream = not self.stream
        self._print_markdown(
            f"* Streaming mode is now {'enabled' if self.stream else 'disabled'}."
        )

    def do_new(self, _):
        """
        Start a new conversation

        Examples:
            {leader}new
        """
        self.chatgpt.new_conversation()
        self._print_markdown("* New conversation started.")
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
            Current conversation: {leader}delete
            By conversation ID: {leader}delete 5eea79ce-b70e-11ed-b50e-532160c725b2
            By history ID: {leader}delete 3
            Multiple IDs: {leader}delete 1,5
            Ranges: {leader}delete 1-5
            Complex: {leader}delete 1,3-5,5eea79ce-b70e-11ed-b50e-532160c725b2
        """
        if arg:
            result = self._parse_conversation_ids(arg)
            if isinstance(result, list):
                history = self._fetch_history()
                if history:
                    history_list = [h for h in history.values()]
                    for item in result:
                        if isinstance(item, str) and len(item) == 36:
                            self._delete_conversation(item)
                        else:
                            if item <= len(history_list):
                                conversation = history_list[item - 1]
                                self._delete_conversation(conversation['id'], conversation['title'])
                            else:
                                self._print_markdown("* Cannont delete history item %d, does not exist" % item)
            else:
                self._print_markdown(result)
        else:
            self._delete_current_conversation()

    def do_history(self, arg):
        """
        Show recent conversation history

        Arguments;
            limit: limit the number of messages to show (default 20)
            offset: offset the list of messages by this number

        Examples:
            {leader}history
            {leader}history 10
            {leader}history 10 5
        """
        limit = DEFAULT_HISTORY_LIMIT
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
        history = self._fetch_history(limit=limit, offset=offset)
        if history:
            history_list = [h for h in history.values()]
            self._print_markdown("## Recent history:\n\n%s" % "\n".join(["1. %s: %s (%s)" % (datetime.datetime.strptime(h['create_time'], "%Y-%m-%dT%H:%M:%S.%f").strftime("%Y-%m-%d %H:%M"), h['title'], h['id']) for h in history_list]))

    def do_nav(self, arg):
        """
        Navigate to a past point in the conversation

        Arguments:
            id: prompt ID

        Examples:
            {leader}nav 2
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

        (
            self.chatgpt.conversation_id,
            self.chatgpt.parent_message_id,
        ) = self.message_map[msg_id]
        self._update_message_map()
        self._write_log_context()
        self._print_markdown(
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
            Get current conversation title: {leader}title
            Set current conversation title: {leader}title new title
            Set conversation title using history ID: {leader}title 1
        """
        if arg:
            history = self._fetch_history()
            history_list = [h for h in history.values()]
            conversation_id = None
            id = None
            try:
                id = int(arg)
            except Exception:
                pass
            if id:
                if id <= len(history_list):
                    conversation_id = history_list[id - 1]["id"]
                else:
                    self._print_markdown("* Cannot set title on history item %d, does not exist" % id)
                    return
            if conversation_id:
                new_title = input("Enter new title for '%s': " % history[conversation_id]["title"])
            else:
                new_title = arg
            self._set_title(new_title, conversation_id)
        else:
            if self.chatgpt.conversation_id:
                history = self._fetch_history()
                if self.chatgpt.conversation_id in history:
                    self._print_markdown("* Title: %s" % history[self.chatgpt.conversation_id]['title'])
                else:
                    self._print_markdown("* Cannot load conversation title, not in history.")
            else:
                self._print_markdown("* Current conversation has no title, you must send information first")

    def do_chat(self, arg):
        """
        Retrieve chat content

        Arguments:
            conversation_id: The ID of the conversation
            ...or...
            history_id: The history ID

        Examples:
            By conversation ID: {leader}chat 5eea79ce-b70e-11ed-b50e-532160c725b2
            By history ID: {leader}chat 2
        """
        conversation_id = None
        title = None
        if arg:
            if len(arg) == 36:
                conversation_id = arg
                title = arg
            else:
                history = self._fetch_history()
                history_list = [h for h in history.values()]
                id = None
                try:
                    id = int(arg)
                except Exception:
                    self._print_markdown("* Invalid chat history item %d, must be in integer" % id)
                    return
                if id:
                    if id <= len(history_list):
                        conversation_id = history_list[id - 1]["id"]
                        title = history_list[id - 1]["title"]
                    else:
                        self._print_markdown("* Cannot retrieve chat content on history item %d, does not exist" % id)
                        return
        else:
            if not self.chatgpt.conversation_id:
                self._print_markdown("* Current conversation is empty, you must send information first")
                return
        conversation_data = self.chatgpt.get_conversation(conversation_id)
        if conversation_data:
            messages = self.chatgpt.conversation_data_to_messages(conversation_data)
            if title:
                self._print_markdown(f"### {title}")
            self._print_markdown(self._conversation_from_messages(messages))
        else:
            self._print_markdown("* Could not load chat content")

    def do_switch(self, arg):
        """
        Switch to chat

        Arguments:
            conversation_id: The ID of the conversation
            ...or...
            history_id: The history ID

        Examples:
            By conversation ID: {leader}switch 5eea79ce-b70e-11ed-b50e-532160c725b2
            By history ID: {leader}switch 2
        """
        conversation_id = None
        title = None
        if arg:
            if len(arg) == 36:
                conversation_id = arg
                title = arg
            else:
                history = self._fetch_history()
                history_list = [h for h in history.values()]
                id = None
                try:
                    id = int(arg)
                except Exception:
                    self._print_markdown("* Invalid chat history item %d, must be in integer" % id)
                    return
                if id:
                    if id <= len(history_list):
                        conversation_id = history_list[id - 1]["id"]
                        title = history_list[id - 1]["title"]
                    else:
                        self._print_markdown("* Cannot retrieve chat content on history item %d, does not exist" % id)
                        return
        else:
            self._print_markdown("* Argument required, ID or history ID")
            return
        if conversation_id and conversation_id == self.chatgpt.conversation_id:
            self._print_markdown("* You are already in chat: %s" % title)
            return
        conversation_data = self.chatgpt.get_conversation(conversation_id)
        if conversation_data:
            messages = self.chatgpt.conversation_data_to_messages(conversation_data)
            message = messages.pop()
            self.chatgpt.conversation_id = conversation_id
            self.chatgpt.parent_message_id = message['id']
            self._update_message_map()
            self._write_log_context()
            if title:
                self._print_markdown(f"### Switched to: {title}")
        else:
            self._print_markdown("* Could not switch to chat")

    def do_ask(self, line):
        """
        Ask a question to ChatGPT

        It is purely optional.

        Examples:
            {leader}ask what is 6+6 (is the same as 'what is 6+6')
        """
        return self.default(line)

    def default(self, line):
        if not line:
            return

        if self.stream:
            response = ""
            first = True
            for chunk in self.chatgpt.ask_stream(line):
                if first:
                    print("")
                    first = False
                print(chunk, end="")
                sys.stdout.flush()
                response += chunk
            print("\n")
        else:
            response = self.chatgpt.ask(line)
            print("")
            self._print_markdown(response)

        self._write_log(line, response)
        self._update_message_map()

    def do_session(self, _):
        """
        Refresh session information

        This can resolve errors under certain scenarios.

        Examples:
            {leader}session
        """
        self.chatgpt.refresh_session()
        usable = (
            "The session appears to be usable."
            if "accessToken" in self.chatgpt.session
            else "The session is not usable.  Try `install` mode."
        )
        self._print_markdown(f"* Session information refreshed.  {usable}")

    def do_read(self, _):
        """
        Begin reading multi-line input

        Allows for entering more complex multi-line input prior to sending it to ChatGPT.

        Examples:
            {leader}read
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

        self.default(prompt)

    def do_editor(self, args):
        """
        Open an editor for entering a command

        When the editor is closed, the content is sent to ChatGPT.

        Requires 'vipe' executable in your path.

        Arguments:
            default_text: The default text to open the editor with

        Examples:
            {leader}editor
            {leader}editor some text to start with
        """
        try:
            process = subprocess.Popen(['vipe'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        except FileNotFoundError:
            self._print_markdown(
                "Failed to execute `vipe`, must be installed and in path. Install package `moreutils`. `brew install moreutils` on macOS and `apt install moreutils` on Ubuntu.")
            return
        process.stdin.write(args.encode())
        process.stdin.close()
        process.wait()
        output = process.stdout.read().decode()
        print(output)
        self.default(output)

    def do_file(self, arg):
        """
        Send a prompt read from the named file

        Arguments:
            file_name: The name of the file to read from

        Examples:
            {leader}file myprompt.txt
        """
        try:
            fileprompt = open(arg, encoding="utf-8").read()
        except Exception:
            self._print_markdown(f"Failed to read file '{arg}'")
            return
        self.default(fileprompt)

    def _open_log(self, filename) -> bool:
        try:
            if os.path.isabs(filename):
                self.logfile = open(filename, "a", encoding="utf-8")
            else:
                self.logfile = open(os.path.join(os.getcwd(), filename), "a", encoding="utf-8")
        except Exception:
            self._print_markdown(f"Failed to open log file '{filename}'.")
            return False
        return True

    def do_log(self, arg):
        """
        Enable/disable logging to a file

        Arguments:
            file_name: The name of the file to write to

        Examples:
            Log to file: {leader}log mylog.txt
            Disable logging: {leader}log
        """
        if arg:
            if self._open_log(arg):
                self._print_markdown(f"* Logging enabled, appending to '{arg}'.")
        else:
            self.logfile = None
            self._print_markdown("* Logging is now disabled.")

    def do_context(self, arg):
        """
        Load an old context from the log

        Arguments:
            context_string: a context string from logs

        Examples:
            {leader}context 67d1a04b-4cde-481e-843f-16fdb8fd3366:0244082e-8253-43f3-a00a-e2a82a33cba6
        """
        try:
            (conversation_id, parent_message_id) = arg.split(":")
            assert conversation_id == "None" or len(conversation_id) == 36
            assert len(parent_message_id) == 36
        except Exception:
            self._print_markdown("Invalid parameter to `context`.")
            return
        self._print_markdown("* Loaded specified context.")
        self.chatgpt.conversation_id = (
            conversation_id if conversation_id != "None" else None
        )
        self.chatgpt.parent_message_id = parent_message_id
        self._update_message_map()
        self._write_log_context()

    def do_exit(self, _):
        """
        Exit the ChatGPT shell

        Examples:
            {leader}exit
        """
        pass

    def do_quit(self, _):
        """
        Exit the ChatGPT shell

        Examples:
            {leader}quit
        """
        pass

    def cmdloop(self):
        print("")
        self._print_markdown("### %s" % self.intro)
        while True:
            try:
                user_input = self.prompt_session.prompt(self.prompt)
            except KeyboardInterrupt:
                continue  # Control-C pressed. Try again.
            except EOFError:
                break  # Control-D pressed.

            text = user_input.strip()
            if not text:
                continue
            leader = text[0]
            if leader == COMMAND_LEADER or leader == LEGACY_COMMAND_LEADER:
                text = text[1:]
                parts = [arg.strip() for arg in text.split(maxsplit=1)]
                command = parts[0]
                argument = parts[1] if len(parts) > 1 else ''
                if leader == LEGACY_COMMAND_LEADER:
                    self.legacy_command_leader_warning(command)
                    continue
                if command == "exit" or command == "quit":
                    break
            else:
                if text == '?':
                    command = 'help'
                    argument = ''
                else:
                    command = DEFAULT_COMMAND
                    argument = text

            if command == 'help':
                self.help(argument)
            else:
                if command in self.commands:
                    method = getattr(__class__, f"do_{command}")
                    try:
                        response = method(self, argument)
                    except Exception as e:
                        print(repr(e))
                    else:
                        if response:
                            print(response)
                else:
                    print(f'Unknown command: {command}')

        print('GoodBye!')
