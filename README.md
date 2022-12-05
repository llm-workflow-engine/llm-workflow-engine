# Fork Notes

This project is a fork of [mmabrouk/chatgpt-wrapper](https://github.com/mmabrouk/chatgpt-wrapper).

Here's whats different about it:

* Works by injecting JS in to the browser to interact with the chatgpt API directly, rather than interacting with the website.  This is more responsive and robust, and produces higher quality output.
* Use `rich` library to render ChatGPT's markdown output in a terminal-friendly way.
* Add a multi-line input system (blank line to end input)
* Switched the browser to Firefox.  In my experience, Firefox can log in to Google oauth and Chromium can not.


The contributions on this fork are licensed under the MIT license to match the parent project.

-------


# ChatGPT Wrapper


ChatGPT Wrapper is an open-source tool unofficial API that lets you interact with ChatGPT in Python and from Terminal.

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

```
$ chatGPT
```

Or get the response for one question

``` bash
$ chatGPT Write a grep command to find all names of functions in a python script
```
<img width="600" alt="Screenshot 2022-12-03 at 21 11 44" src="https://user-images.githubusercontent.com/4510758/205460076-1defee06-7d62-4cfa-9f31-714d9cc669fc.png">

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

### shell
You can run the command chatGPT in shell and you can talk with it in shell

## Contributing

We welcome contributions to ChatGPT Wrapper! If you have an idea for a new feature or have found a bug, please open an issue on the GitHub repository.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- This project is a modification from [Taranjeet](https://github.com/taranjeet/chatgpt-api) code which is a modification of [Daniel Gross](https://github.com/danielgross/whatsapp-gpt) code.

