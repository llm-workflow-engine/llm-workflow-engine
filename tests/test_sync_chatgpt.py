#!/usr/bin/env python

from chatgpt_wrapper import ChatGPT
from chatgpt_wrapper.core.config import Config

def main():
    config = Config()
    config.set('browser.debug', True)
    config.set('debug.log.enabled', True)
    gpt = ChatGPT(config)
    response1 = gpt.ask("Say, bot1!")
    print(response1)

main()
