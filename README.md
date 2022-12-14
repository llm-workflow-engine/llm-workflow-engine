# ChatGPT CLI and Python Wrapper

ChatGPT Wrapper is an open-source unofficial Python API and CLI that lets you interact with ChatGPT.

## Highlights

🤖 Programmable ChatGPT. The ChatGPT Wrapper lets you use the powerful ChatGPT bot in your Python scripts or on the command line, making it easy to leverage its functionality into your projects.

💬 Runs in Shell. You can call and interact with ChatGPT in the terminal

## How it works

Run an interactive CLI in the terminal:

``` bash
$ chatgpt
Provide a prompt for ChatGPT, or type help or ? to list commands.
1> 
```

Or just get a quick response for one question:

``` bash
$ chatgpt What is six times seven?

Six times seven is 42.      
```

Here's a short demo of some of the CLI features:
https://user-images.githubusercontent.com/233113/206799611-8807f659-cd4c-449f-9937-843153533a15.mp4

See below for details on using ChatGPT as an API.

## Requirements

To use this repository, you will need to have the following packages installed:

`setuptools`: This package is used to create and manage Python packages.
You can install it using `pip install setuptools`.

## Installation

You can install the latest version of this software directly from github with pip:

```bash
pip install git+https://github.com/mmabrouk/chatgpt-wrapper
```

This will install chatgpt-wrapper and it's dependencies.  

Before starting the program, you will need to install a browser in playwright (if you haven't already).  The program will use firefox by default.

```
playwright install firefox
```

With that done, you should start up the program in `install` mode, which will open up a browser window. 

```bash
chatgpt install
```

Log in to ChatGPT in the browser window, then stop the program.  After doing this, restart the program without the `install` parameter to begin using it.

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

## Upcoming Features

- [ ] Async mode
- [ ] Remove reliance on playwright
- [ ] Improve error messaging
- [ ] Automatic installation start when not logged in

Note: We welcome pull requests for any of the above features, or any other improvements you'd like to see in the project.

## Contributing

We welcome contributions to ChatGPT Wrapper! If you have an idea for a new feature or have found a bug, please open an issue on the GitHub repository.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- This project is a modification from [Taranjeet](https://github.com/taranjeet/chatgpt-api) code which is a modification of [Daniel Gross](https://github.com/danielgross/whatsapp-gpt) code.

