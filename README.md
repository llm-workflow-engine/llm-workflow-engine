# ChatGPT CLI and Python Wrapper

ChatGPT Wrapper is an open-source unofficial Python API and CLI that lets you interact with ChatGPT.

## Highlights

🤖 Programmable ChatGPT. The ChatGPT Wrapper lets you use the powerful ChatGPT bot in your *Python scripts* or on the *command line*, making it easy to leverage its functionality into your projects.

💬 Runs in Shell. You can call and interact with ChatGPT in the terminal

## How it works

Run an interactive CLI in the terminal:

![kod](https://user-images.githubusercontent.com/4510758/212907070-602d61fe-708d-4a39-aaa2-0e84fcf88dcf.png)

Or just get a quick response for one question:

![kod(1)](https://user-images.githubusercontent.com/4510758/212906773-666be6fe-90e1-4f5e-b962-7748143bd744.png)

See below for details on using ChatGPT as an API from Python.

## Requirements

To use this repository, you need  `setuptools` installed. You can install it using `pip install setuptools`.

## Installation

1. Install the latest version of this software directly from github with pip:
```bash
pip install git+https://github.com/mmabrouk/chatgpt-wrapper
```

2. Install a browser in playwright (if you haven't already).  The program will use firefox by default.

```
playwright install firefox
```

3. Start up the program in `install` mode. This opens up a browser window. Log in to ChatGPT in the browser window, then stop the program. 

```bash
chatgpt install
```

4. Restart the program without the `install` parameter to begin using it.

Note: For more help, this [Blog post](https://medium.com/geekculture/using-chatgpt-in-python-eeaed9847e72) provides a visual step-by-step guide for installing this library.

## Usage

### Shell

The shell includes some nice features:
* It provides commands to start a new conversation, or navigate to past points in the conversation.
* It provides a command that allows the user to choose between rendered markdown and streaming output (can't have both).
* It provides a logging option, and the ability to restore any context that's been logged, even from old sessions.
* It provides a command to read prompts from files, and a command to support reading multi-line prompts.

### Python

To use the `ChatGPT` class as an API for talking to ChatGPT, create an instance of the class and use the `ask` method to send a message to OpenAI and receive the response. For example:

```python
from chatgpt_wrapper import ChatGPT

bot = ChatGPT()
response = bot.ask("Hello, world!")
print(response)  # prints the response from chatGPT
```

The say method takes a string argument representing the message to send to ChatGPT, and returns a string representing the response received from ChatGPT.

You may also stream the response as it comes in from ChatGPT in chunks using the `ask_stream` generator.

## Projects built with chatgpt-wrapper

  - [bookast: ChatGPT Podcast Generator For Books](https://github.com/SamMethnani/bookast)
  - [ChatGPT.el: ChatGPT in Emacs](https://github.com/joshcho/ChatGPT.el)
  - [ChatGPT Reddit Bot](https://github.com/PopDaddyGames/ChatGPT-RedditBot)

## Contributing

We welcome contributions to ChatGPT Wrapper! If you have an idea for a new feature or have found a bug, please open an issue on the GitHub repository.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Updates
- 18/01/2022: v0.3.8 - Commands now are run only using !. For instance to enable read mode (for copy-paste and long prompts) you need to write now `!read` instead of `read`. This is to avoid conflicts with the chatgpt prompts. Fixed timeout issue.
- 17/01/2022: v0.3.7 - Added timeout to `ask` method to prevent hanging. Fixed return to terminal breakdown. Streaming output now is activated by default.


## Acknowledgments

- This project is a modification from [Taranjeet](https://github.com/taranjeet/chatgpt-api) code which is a modification of [Daniel Gross](https://github.com/danielgross/whatsapp-gpt) code.

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=mmabrouk/chatgpt-wrapper&type=Date)](https://star-history.com/#mmabrouk/chatgpt-wrapper&Date)
