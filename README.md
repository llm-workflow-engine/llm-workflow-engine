# ChatGPT Python Wrapper


ChatGPT Wrapper is an open-source tool that lets you use ChatGPT programmably in Python or the terminal using Playwright.

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

https://user-images.githubusercontent.com/4510758/205457296-db895975-4efb-4a08-8a5c-4ac1e558f693.mp4

## Requirements

To use this repository, you will need to have the following packages installed:

`setuptools`: This package is used to create and manage Python packages.
You can install it using `pip install setuptools`.

## Installation

Clone this repository and install the required dependencies:

```bash
pip install git+https://github.com/mmabrouk/chatgpt-wrapper
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

### shell
You can run the command chatGPT in shell and you can talk with it in shell

## Contributing

We welcome contributions to ChatGPT Wrapper! If you have an idea for a new feature or have found a bug, please open an issue on the GitHub repository.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- This project is a modification from [Taranjeet](https://github.com/taranjeet/chatgpt-api) code which is a modification of [Daniel Gross](https://github.com/danielgross/whatsapp-gpt) code.

