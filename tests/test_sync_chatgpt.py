#!/usr/bin/env python

from chatgpt_wrapper import ChatGPT
from chatgpt_wrapper.config import Config

def main():
    config = Config()
    config.set('browser.debug', True)
    gpt = ChatGPT(config)
    response1 = gpt.ask("Say, bot1!")
    print(response1)

main()
