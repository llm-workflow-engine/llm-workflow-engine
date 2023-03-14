import csv
import os
import time
import tempfile
import urllib.request

from chatgpt_wrapper.config import Config
from chatgpt_wrapper.logger import Logger
import chatgpt_wrapper.debug as debug
if False:
    debug.console(None)

PROMPTS_URI = "https://github.com/f/awesome-chatgpt-prompts/raw/main/prompts.csv"

class Awesome:
    def __init__(self, config=None):
        self.config = config or Config()
        self.config.set('log.console.level', 'DEBUG')
        self.log = Logger(self.__class__.__name__, self.config)
        self.prompts_uri = PROMPTS_URI
        self.reset_prompts()

    def reset_prompts(self):
        self.log.info("Resetting prompts")
        self.make_prompts_temp_file()
        self.prompts_downloaded = False
        self.loaded_prompts = {}

    def make_prompts_temp_file(self):
        self.prompts_temp_file = os.path.join(tempfile.gettempdir(), f"awesome-prompts-{int(time.time())}.csv")
        self.log.debug(f"Created prompts temp file: {self.prompts_temp_file}")

    def list_prompts(self):
        return self.loaded_prompts

    def get_prompts(self):
        if not self.prompts_downloaded:
            self.log.info(f"Downloading prompts from {self.prompts_uri}")
            try:
                with urllib.request.urlopen(self.prompts_uri) as response:
                    data = response.read()
            except Exception as e:
                self.log.error(f"Error downloading prompts file: {e}")
                return
            try:
                with open(self.prompts_temp_file, 'wb') as out_file:
                    out_file.write(data)
                self.prompts_downloaded = True
            except Exception as e:
                self.log.error(f"Error writing prompts file: {e}")

    def load_prompts(self):
        self.get_prompts()
        if not self.loaded_prompts:
            with open(self.prompts_temp_file) as f:
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
