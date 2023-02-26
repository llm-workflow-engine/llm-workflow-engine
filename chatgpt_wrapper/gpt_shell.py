import cmd
import os
import platform
import re
import sys
import datetime
import subprocess
import string
import readline

from rich.console import Console
from rich.markdown import Markdown

console = Console()

# use pyreadline3 instead of readline on windows
is_windows = platform.system() == "Windows"

DEFAULT_HISTORY_LIMIT = 20

class GPTShell(cmd.Cmd):
    """
    A `cmd` interpreter that serves as a front end to the ChatGPT class
    """

    # overrides
    intro = "Provide a prompt for ChatGPT, or type !help or ? to list commands."
    prompt = "> "
    doc_header = "Documented commands (type !help <topic>):"
    identchars = string.ascii_letters + string.digits + '_' + '!'

    # our stuff
    prompt_number = 0
    chatgpt = None
    message_map = {}
    stream = False
    logfile = None

    def parseline(self, line):
        """Parse the line into a command name and a string containing
        the arguments.  Returns a tuple containing (command, args, line).
        'command' and 'args' may be None if the line couldn't be parsed.
        """
        line = line.strip()
        if not line:
            return None, None, line
        elif line[0] == '?':
            line = 'help ' + line[1:]
        i, n = 0, len(line)
        while i < n and line[i] in self.identchars: i = i+1
        cmd, arg = line[:i], line[i:].strip()
        return cmd, arg, line

    def complete(self, text, state):
        """Return the next possible completion for 'text'.
        If a command has not been entered, then complete against command list.
        Otherwise try to call complete_<command> to get list of completions.
        """
        origline = readline.get_line_buffer()
        line = origline.lstrip()
        if line[0] == '!':
            text = "!" + text
        if state == 0:
            stripped = len(origline) - len(line)
            begidx = readline.get_begidx() - stripped
            endidx = readline.get_endidx() - stripped
            if begidx>0:
                cmd, args, line = self.parseline(line)
                if cmd == '':
                    compfunc = self.command_names
                else:
                    if cmd in self.command_names():
                        try:
                            compfunc = getattr(self, 'complete_' + cmd[1:])
                        except AttributeError:
                            compfunc = self.completedefault
                    else:
                        compfunc = self.command_names_filtered
            else:
                compfunc = self.command_names
            self.completion_matches = compfunc(text, line, begidx, endidx)
        try:
            if line[0] == '!':
                return self.completion_matches[state][1:] + ' '
            else:
                return self.completion_matches[state]
        except IndexError:
            return None

    def command_names(self, *ignored):
        return [('!%s' % a[3:]) for a in self.get_names() if a.startswith("do_")]

    def command_names_filtered(self, text, *ignored):
        return [a for a in self.command_names() if a.startswith(text)]

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

    def _parse_conversation_ids(self, string):
        items = [item.strip() for item in string.split(',')]
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

    def emptyline(self):
        """
        override cmd.Cmd.emptyline so it does not repeat
        the last command when you hit enter
        """
        return

    def do_stream(self, _):
        "`!stream` toggles between streaming mode (streams the raw response from ChatGPT) and markdown rendering (which cannot stream)."
        self.stream = not self.stream
        self._print_markdown(
            f"* Streaming mode is now {'enabled' if self.stream else 'disabled'}."
        )

    def do_new(self, _):
        "`!new` starts a new conversation."
        self.chatgpt.new_conversation()
        self._print_markdown("* New conversation started.")
        self._update_message_map()
        self._write_log_context()

    def do_delete(self, arg):
        "`!delete` delete a conversation by conversation or history ID, or current conversation. Example: `!delete 1,3-5` or `!delete`"
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
        "`!history` show recent conversation history, default 20 offset 0, Example `!history` or `!history 10` or `!history 10 5`"
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
        "`!nav` lets you navigate to a past point in the conversation. Example: `nav 2`"

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
        "`!title` Show title of current conversation, or set a new title. Example: `!title` or `!title new title`"
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
        "`!chat` Retrieve chat content by ID or history ID. Example: `!chat [id]` or `!chat 2`"
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
        "`!switch` Switch to chat by ID or history ID. Example: `!switch [id]` or `!switch 2`"
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


    def do_exit(self, _):
        "`!exit` closes the program."
        sys.exit(0)

    def do_quit(self, arg):
        "`!quit` closes the program."
        self.do_exit(arg)

    def do_ask(self, line):
        "`!ask` asks a question to chatgpt. It is purely optional. Example: `!ask what is 6+6` is the same as `what is 6+6`"
        return self.default(line)

    def replace_file_strings(self, string):
        # Regular expression to find all occurrences of !file and their arguments
        pattern = r"!file\s+(\S+)"

        # Search for all matches of the regular expression in the string
        matches = re.findall(pattern, string)

        # Loop through each match and replace the corresponding substring
        for match in matches:
            print("handle file" + match)
            filename = match
            if os.path.isfile(filename):
                with open(filename, "r") as f:
                    file_contents = f.read()
                    # add the file content as seperated segment. Good way to go?
                    string = "\n\n" + string.replace("!file " + filename, file_contents) + "\n\n"
            else:
                print("File not found: " + filename)

        print("returned string: " + string)

        return string

    def default(self, line):
        if not line:
            return

        # find in the line all "!file" entries with the following argument and replace the file content
        line = self.replace_file_strings(line)

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
        "`!session` refreshes your session information.  This can resolve errors under certain scenarios."
        self.chatgpt.refresh_session()
        usable = (
            "The session appears to be usable."
            if "accessToken" in self.chatgpt.session
            else "The session is not usable.  Try `install` mode."
        )
        self._print_markdown(f"* Session information refreshed.  {usable}")

    def do_read(self, _):
        "`!read` begins reading multi-line input."
        ctrl_sequence = "^z" if is_windows else "^d"
        self._print_markdown(f"* Reading prompt, hit {ctrl_sequence} when done, or write line with /end.")

        if not is_windows:
            readline.set_auto_history(False)

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

        if not is_windows:
            readline.set_auto_history(True)
            readline.add_history(prompt)

        self.default(prompt)

    def do_editor(self, args):
        "`!editor` Open an editor for entering a command (requires `vipe` executable). `!editor some default text`"
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
        "`!file` sends a prompt read from the named file.  Example: `file myprompt.txt`"
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
        "`!log` enables logging to a file.  Example: `log mylog.txt` to enable, or `log` to disable."
        if arg:
            if self._open_log(arg):
                self._print_markdown(f"* Logging enabled, appending to '{arg}'.")
        else:
            self.logfile = None
            self._print_markdown("* Logging is now disabled.")

    def do_context(self, arg):
        "`!context` lets you load old contexts from the log.  It takes one parameter; a context string from logs."
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

    def precmd(self, line):
        if len(line) > 0 and line[0] == "!":
            line = line[1:]
        elif len(line) > 0 and line[0] == "?":
            pass
        else:
            line = "ask " + line
        return line

    def complete_help(self, text, line, begidx, endidx):
        if not text:
            completions = sorted(self.command_names())
        else:
            completions = sorted([a for a in self.command_names() if a.startswith(text)])
        return completions

    def do_help(self, arg):
        'List available commands with "!help" or detailed help with "!help cmd".'
        if arg:
            # XXX check arg syntax
            if arg[0] == "!":
                arg = arg[1:]
            try:
                func = getattr(self, 'help_' + arg)
            except AttributeError:
                try:
                    doc = getattr(self, 'do_' + arg).__doc__
                    if doc:
                        self.stdout.write("%s\n" % str(doc))
                        return
                except AttributeError:
                    pass
                self.stdout.write("%s\n" % str(self.nohelp % (arg,)))
                return
            func()
        else:
            names = self.get_names()
            cmds_doc = []
            cmds_undoc = []
            help = {}
            for name in names:
                if name[:5] == 'help_':
                    help[name[5:]] = 1
            names.sort()
            # There can be duplicates if routines overridden
            prevname = ''
            for name in names:
                if name[:3] == 'do_':
                    if name == prevname:
                        continue
                    prevname = name
                    cmd = name[3:]
                    if cmd in help:
                        cmds_doc.append("!"+cmd)
                        del help[cmd]
                    elif getattr(self, name).__doc__:
                        cmds_doc.append("!"+cmd)
                    else:
                        cmds_undoc.append("!"+cmd)
            self.stdout.write("%s\n" % str(self.doc_leader))
            self.print_topics(self.doc_header,   cmds_doc,   15, 80)
            self.print_topics(self.misc_header,  list(help.keys()), 15, 80)
            self.print_topics(self.undoc_header, cmds_undoc, 15, 80)
