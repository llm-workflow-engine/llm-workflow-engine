# ChatGPT CLI and Python Wrapper


ChatGPT Wrapper is an open-source tool unofficial API that lets you interact with ChatGPT in Python and as a CLI.

## Highlights

🤖 Programmable ChatGPT. The ChatGPT Wrapper lets you use the powerful ChatGPT bot in your Python scripts or on the command line, making it easy to leverage its functionality into your projects.

💬 Runs in Shell. You can call and interact with ChatGPT in the terminal

## How it works

Here's an example of how to use the ChatGPT Wrapper in Python:

```python
from chatgpt_wrapper import ChatGPT 
chatbot = ChatGPT()
while True:
    inp = input("You: ")
    response = chatbot.ask(inp)
    print("\nChatGPT: " + response + "\n")
```

You can also use the ChatGPT Wrapper on the command line:

Run an interactive session in the terminal by using

``` bash
$ chatgpt
```

Or get the response for one question

``` bash
$ chatgpt What is six times seven?
```

https://user-images.githubusercontent.com/233113/206799611-8807f659-cd4c-449f-9937-843153533a15.mp4

## Requirements

To use this repository, you will need to have the following packages installed:

`setuptools`: This package is used to create and manage Python packages.
You can install it using `pip install setuptools`.

## Installation

Clone this repository and install the required dependencies:

```bash
pip install git+https://github.com/mmabrouk/chatgpt-wrapper
```

Setup the script by logging in to your openai account for the first time only.

```bash
chatgpt install
```

## Usage

### Python
To use the `ChatGPT` class, create an instance of the class and use the `ask` method to send a message to OpenAI and receive the response. For example:

```python
from chatgpt_wrapper import ChatGPT

bot = ChatGPT()
response = bot.ask("Hello, world!")
print(response)  # prints the response from chatGPT
```

The say method takes a string argument representing the message to send to ChatGPT, and returns a string representing the response received from ChatGPT.

You may also stream the response as it comes in from chatGPT in chunks using the `ask_stream` generator.

### Shell

The `chatgpt` command can be run in the shell, allowing you to have a conversation with ChatGPT directly in the terminal. Simply run the command and start chatting!

The shell includes some nice features:
* It provides commands to navigate to past points in the conversation.
* It provides a command to start new conversations.
* It allows the user to choose between markdown and streaming output.

## Upcoming Features

- [ ] Async mode
- [ ] Remove reliance on playwright
- [ ] Improve error messaging
- [ ] Automatic installation start when not logged in

Note: We welcome pull requests for any of the above features, or any other improvements you'd like to see in the project.

## Updates

- Thanks to @Tecuya for the following improvements:
  - Improved inputs in the CLI, including support for history and arrow keys
  - Fancy markdown rendering for outputs
  - Fixes for the login process
  - The ability to clear conversations
  - Direct interaction with the API

## Contributing

We welcome contributions to ChatGPT Wrapper! If you have an idea for a new feature or have found a bug, please open an issue on the GitHub repository.


## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- This project is a modification from [Taranjeet](https://github.com/taranjeet/chatgpt-api) code which is a modification of [Daniel Gross](https://github.com/danielgross/whatsapp-gpt) code.

