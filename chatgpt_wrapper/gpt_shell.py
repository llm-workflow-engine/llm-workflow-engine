import cmd
import os
import platform
import sys

from rich.console import Console
from rich.markdown import Markdown

from chatgpt_wrapper.chatgpt import ChatGPT

console = Console()

# use pyreadline3 instead of readline on windows
is_windows = platform.system() == "Windows"
if is_windows:
    import pyreadline3  # noqa: F401
else:
    import readline


class GPTShell(cmd.Cmd):
    """
    A `cmd` interpreter that serves as a front end to the ChatGPT class
    """

    # overrides
    intro = "Provide a prompt for ChatGPT, or type !help or ? to list commands."
    prompt = "> "
    doc_header = "Documented commands (type !help <topic>):"

    # our stuff
    prompt_number = 0
    chatgpt = None
    message_map = {}
    stream = False
    logfile = None

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

    def do_exit(self, _):
        "`!exit` closes the program."
        sys.exit(0)

    def do_ask(self, line):
        "`!ask` asks a question to chatgpt. It is purely optional. Example: `!ask what is 6+6` is the same as `what is 6+6`"
        return self.default(line)

    def default(self, line):

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
