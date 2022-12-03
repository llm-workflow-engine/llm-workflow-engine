# ChatGPT Python Wrapper

A simple Python class that allows you to interact with OpenAI's ChatGPT using Playwright.

Requirements

To use this repository, you will need to have the following packages installed:

`setuptools`: This package is used to create and manage Python packages. You can install it using `pip install setuptools`.
## Installation

Clone this repository and install the required dependencies:

```bash
git clone https://github.com/mmabrouk/chatgpt-wrapper
pip install chatgpt-wrapper
```


## Usage

### In Python
To use the `ChatGPT` class, create an instance of the class and use the `ask` method to send a message to OpenAI and receive the response. For example:

```python
from chatgpt_wrapper import ChatGPT

bot = ChatGPT()
response = bot.ask("Hello, world!")
print(response)  # prints the response from chatGPT
```

The say method takes a string argument representing the message to send to ChatGPT, and returns a string representing the response received from ChatGPT.

### In shell
You can run the command chatGPT in shell and you can talk with it in shell

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- This project is a modification from [Taranjeet](https://github.com/taranjeet/chatgpt-api) code which is a modification of [Daniel Gross](https://github.com/danielgross/whatsapp-gpt) code.

