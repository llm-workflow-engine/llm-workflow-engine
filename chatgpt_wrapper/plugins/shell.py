import os
import platform
import subprocess

from langchain.schema import HumanMessage, SystemMessage

from chatgpt_wrapper.core.plugin import Plugin
import chatgpt_wrapper.core.util as util

class Shell(Plugin):

    def default_config(self):
        return {
            'command': {
                'confirm': True,
            },
            'shell': {
                'path': None,
            },
        }

    def setup(self):
        self.log.info(f"Setting up shell plugin, running with backend: {self.backend.name}")
        self.confirm_command = self.config.get('plugins.shell.command.confirm')
        self.shell_path = self.config.get('plugins.shell.shell.path')

    def build_prompt_to_command_prompt(self, shell, command):
        shell = shell.strip()
        command = command.strip()
        prompt = """Write a shell command that works in the following shell: %s

The command must accomplish this task:

%s

Return ONLY the command, no other explanation, words, code highlighting, or text.
""" % (shell, command)

        messages = [
            SystemMessage(content="You are a helpful assistant that is very good at writing shell commands who thinks step by step."),
            HumanMessage(content=prompt),
        ]
        return messages


    def get_default_shell(self) -> str:
        """
        Discovers the user's default shell and returns it.
        This method works on major operating systems including Windows, Unix, Linux, and macOS.

        :return: The default shell as a string
        """

        os_name = platform.system()
        if os_name == "Windows":
            return os.environ.get("COMSPEC", "cmd.exe")
        elif os_name in ("Linux", "Darwin"):
            user = os.environ.get("USER")
            try:
                with open("/etc/passwd", "r") as passwd_file:
                    for line in passwd_file:
                        if line.startswith(user + ":"):
                            return line.strip().split(":")[-1]
            except FileNotFoundError:
                pass
            return os.environ.get("SHELL", "/bin/sh")
        else:
            raise NotImplementedError(f"Default shell detection not implemented for {os_name}")

    def get_shell_command(self, prompt):
        shell = self.shell_path or self.get_default_shell()
        messages = self.build_prompt_to_command_prompt(shell, prompt)
        self.log.debug(f"Fetching shell command with prompt: {prompt}")
        success, result, user_message = self.query_llm(messages)
        return success, result, user_message

    def execute_command(self, command: str) -> tuple:
        """
        This method takes a command as an argument, displays it, and asks for user confirmation before executing it.
        If the user confirms, it executes the command in the user's default shell environment and returns the return code,
        stdout, and stderr as a tuple.

        :param command: The command to be executed
        :return: Tuple containing the return code, stdout, and stderr
        """

        print(f"Command: {command}")
        if self.confirm_command:
            confirmation = input("Do you want to execute this command? (y|yes / n|no) ")
            confirmed = confirmation.lower() in ("y", "yes")
        else:
            confirmed = True
        if confirmed:
            shell = self.get_default_shell()
            self.log.debug(f"Executing shell command in shell '{shell}': {command}")
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, executable=shell)
            stdout, stderr = process.communicate()
            return_code = process.returncode
            self.log.debug(f"Shell command results -- return code: {return_code},  stdout: {stdout}, stderr: {stderr}")
            return return_code, stdout, stderr
        else:
            message = "Shell command execution cancelled."
            self.log.info(message)
            return 1, message, ""

    def format_output(self, stdout, stderr):
        output = f"\n{stdout}"
        if stderr:
            output = f"{stderr}\n\n{output}"
        return output

    def do_shell(self, arg):
        """
        Execute a shell command built by the LLM based on the text prompt provided.

        WARNING:
            USE AT YOUR OWN RISK, YOU ARE RESPONSIBLE FOR VALIDATING THE SHELL COMMAND
            RETURNED BY THE LLM, AND THE OUTCOME OF ITS EXECUTION.

        You must confirm the execution of the shell command returned by the LLM.

        Arguments:
            prompt: The text prompt the LLM should use to build the shell command.

        Examples:
            {COMMAND} print the current working directory
        """
        if not arg:
            return False, arg, "Argument is required"
        util.print_status_message(True, f"Fetching shell command for prompt: {arg}")
        success, result, message = self.get_shell_command(arg)
        if not success:
            return success, result, message
        return_code, stdout, stderr = self.execute_command(message)
        output = self.format_output(stdout, stderr)
        return return_code == 0, arg, output
