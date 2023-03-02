#!/usr/bin/env python

import os
import sys
import logging
import openai

import chatgpt_wrapper.debug as debug



orm = ORM('sqlite:///example.db')
users = orm.get_users()
for user in users:
    conversations = orm.get_conversations(user)
    for conversation in conversations:
        messages = orm.get_messages(conversation)
        for message in messages:
            print(message.message)

DEFAULT_CONSOLE_LOG_LEVEL = logging.DEBUG
DEFAULT_CONSOLE_LOG_FORMATTER = logging.Formatter("%(levelname)s - %(message)s")
DEFAULT_FILE_LOG_LEVEL = logging.DEBUG
DEFAULT_FILE_LOG_FORMATTER = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

RENDER_MODELS = {
    "default": "gpt-3.5-turbo",
    "turbo-0301": "gpt-3.5-turbo-0301",
}

class OpenAIAPI:
    def __init__(self, model=None, debug_log=None):
        self.debug_log = debug_log
        self.log = self._set_logging(self.debug_log)
        self.openai = openai
        self.openai.organization = os.getenv("OPENAI_ORG_ID")
        self.openai.api_key = os.getenv("OPENAI_API_KEY")
        try:
            self.model = RENDER_MODELS[model]
        except KeyError:
            self.model = RENDER_MODELS["default"]

    def _set_logging(self, debug_log):
        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(logging.DEBUG)
        log_console_handler = logging.StreamHandler()
        log_console_handler.setFormatter(DEFAULT_CONSOLE_LOG_FORMATTER)
        log_console_handler.setLevel(DEFAULT_CONSOLE_LOG_LEVEL)
        logger.addHandler(log_console_handler)
        if debug_log:
            log_file_handler = logging.FileHandler(debug_log)
            log_file_handler.setFormatter(DEFAULT_FILE_LOG_FORMATTER)
            log_file_handler.setLevel(DEFAULT_FILE_LOG_LEVEL)
            logger.addHandler(log_file_handler)
        return logger

    def chat(self, message):
        messages = [
            {
                "role": "user",
                "content": message,
            },
        ]
        completion = self.openai.ChatCompletion.create(model=self.model, messages=messages)
        response = completion.choices[0].message.content
        return response

def collect_args():
    args = " ".join(sys.argv[1:])
    return args

if __name__ == "__main__":
    collected_args = collect_args()
    api = OpenAIAPI()
    response = api.chat(collected_args)
    api.log.info(response.strip())
