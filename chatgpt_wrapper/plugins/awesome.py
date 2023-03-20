import csv
import os
import tempfile
import urllib.request

import chatgpt_wrapper.constants as constants
from chatgpt_wrapper.plugin import Plugin
import chatgpt_wrapper.debug as debug
if False:
    debug.console(None)

PROMPTS_URI = "https://github.com/f/awesome-chatgpt-prompts/raw/main/prompts.csv"
PROMPTS_TEMP_FILE = "awesome-prompts.csv"

class Awesome(Plugin):

    def setup(self):
        self.prompts_uri = PROMPTS_URI
        self.make_prompts_temp_file()
        self.reset_prompts()
        self.load_prompts()

    def get_shell_completions(self, _base_shell_completions):
        commands = {}
        help_keys = ['reload'] + list(self.loaded_prompts.keys())
        commands[self.shell.command_with_leader('awesome')] = self.shell.list_to_completion_hash(help_keys)
        return commands

    async def do_awesome(self, arg):
        """
        Use a prompt from Awesome ChatGPT Prompts

        Awesome ChatGPT Prompts is a collection of prompt examples to be used with the ChatGPT model.

        The prompt will be opened in an editor to review and make final adjustments.

        For more information, and a full list of available prompts, see https://github.com/f/awesome-chatgpt-prompts

        Examples:
            Load latest version of prompts: {COMMAND} reload
            Act as a Linux terminal: {COMMAND} Linux Terminal
        """
        if not arg:
            return False, arg, "Argument is required"
        elif arg == 'reload':
            self.shell._print_status_message(True, "Reloading Awesome ChatGPT Prompts")
            self.delete_prompts()
            self.load_prompts()
            return True, None, "Awesome ChatGPT Prompts reloaded"
        elif not self.loaded_prompts:
            return False, None, "Awesome ChatGPT Prompts not loaded, try: %sawesome reload" % constants.COMMAND_LEADER
        elif arg not in self.loaded_prompts:
            return False, arg, f"Unknown Awesome ChatGPT Prompt: {arg}"
        return await self.shell.do_editor(self.loaded_prompts[arg])

    def reset_prompts(self):
        self.log.info("Resetting prompts")
        self.prompts_downloaded = False
        self.loaded_prompts = {}

    def make_prompts_temp_file(self):
        self.prompts_temp_file = os.path.join(tempfile.gettempdir(), PROMPTS_TEMP_FILE)
        self.log.debug(f"Created prompts temp file: {self.prompts_temp_file}")

    def list_prompts(self):
        return self.loaded_prompts

    def get_prompts(self):
        if self.prompts_downloaded:
            return
        elif os.path.exists(self.prompts_temp_file):
            self.prompts_downloaded = True
            return
        self.log.info(f"Downloading prompts from {self.prompts_uri}")
        try:
            with urllib.request.urlopen(self.prompts_uri) as response:
                data = response.read()
        except Exception as e:
            self.log.error(f"Error downloading prompts file: {e}")
            return
        try:
            with open(self.prompts_temp_file, 'w', encoding='utf-8') as out_file:
                out_file.write(data.decode('utf-8'))
            self.prompts_downloaded = True
        except Exception as e:
            self.log.error(f"Error writing prompts file: {e}")

    def load_prompts(self):
        self.get_prompts()
        if not self.loaded_prompts:
            with open(self.prompts_temp_file, encoding='utf-8') as f:
                self.log.info(f"Loading prompts from {self.prompts_temp_file}")
                reader = csv.DictReader(f)
                for row in reader:
                    self.loaded_prompts[row['act']] = row['prompt']

    def delete_prompts(self):
        self.log.info(f"Deleting prompts file: {self.prompts_temp_file}")
        try:
            os.remove(self.prompts_temp_file)
        except Exception as e:
            self.log.error(f"Error deleting prompts file: {e}")
            return
        self.reset_prompts()
