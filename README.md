# ChatGPT CLI and Python Wrapper

ChatGPT Wrapper is an open-source unofficial Python API and CLI that lets you interact with ChatGPT.


## Highlights

🤖 **Programmable ChatGPT**. The ChatGPT Wrapper lets you use the powerful ChatGPT bot in your *Python scripts* or on the *command line*, making it easy to leverage its functionality into your projects.

💬 **Runs in Shell**. You can call and interact with ChatGPT in the terminal

🐍 **Python API**. The ChatGPT Wrapper is a Python library that lets you use ChatGPT in your Python scripts.

🐳 **Docker image**. The ChatGPT Wrapper is also available as a docker image. (experimental)

:test_tube: **Flask API**. You can use the ChatGPT Wrapper as an API. (experimental)

## Release Notes - v0.4.0 - 27/02/2023

### **:fire_engine:Breaking Changes:fire_engine:**

- Command leader changed from '!' to '/'
- Asyncio module is now required to use ChatGPT class directly (refer to [Python usage](#python))

### What is new?
#### New commands
- Added '/quit' command
- Added '/delete' support for history IDs/UUIDs
- Added '/chat' command
- Added '/switch' command
- Added '/title' command
- Added limit/offset support for '/history'
#### New features
- ***Migrated to async Playwright***
- ***Initial API in Flask*** (see [How to use the API](#flask-api))
- Added tab completion for commands
- Added '/tmp' volume for saving Playwright session
- Added CI and CodeQL workflows
- Added simple developer debug module
- Improved session refreshing (***/session now works!***)
- Migrated to Prompt Toolkit

[See commit log for previous updates](#commit-log)

## How it works

Run an interactive CLI in the terminal:

![kod](https://user-images.githubusercontent.com/4510758/212907070-602d61fe-708d-4a39-aaa2-0e84fcf88dcf.png)

Or just get a quick response for one question:

![kod(1)](https://user-images.githubusercontent.com/4510758/212906773-666be6fe-90e1-4f5e-b962-7748143bd744.png)

See below for details on using ChatGPT as an API from Python.

## Requirements

To use this repository, you need  `setuptools` installed. You can install it using `pip install setuptools`. Make sure that you have the last version of pip: `pip install --upgrade pip`
To use the /write command, you need to install vipe. In ubuntu, you can install it with `sudo apt install moreutils`, in macos with `brew install moreutils`.

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

## Tutorials:

- Youtube Tutorial: [How To Use ChatGPT With Unity: Python And API Setup #2](https://www.youtube.com/watch?v=CthF8c8qk4c) includes a step by step guide to installing this repository on a windows machine
- This [Blog post](https://medium.com/geekculture/using-chatgpt-in-python-eeaed9847e72) provides a visual step-by-step guide for installing this library.

## Usage

### Shell

#### Command line arguments

Run `chatgpt --help`

#### One-shot mode

To run the CLI in one-shot mode, simply follow the command with the prompt you want to send to ChatGPT:

```
chatgpt Hello World!
```

#### Interacive mode


To run the CLI in interactive mode, execute it with no additional arguments:

```
chatgpt
```

Once the interactive shell is running, you can see a list of all commands with:

```
/help
```

...or get help for a specific command with:

```
/help <command>
```

### Python

To use the `ChatGPT` class as an API for talking to ChatGPT, create an instance of the class and use the `ask` method to send a message to OpenAI and receive the response. For example:

```python
import asyncio
from chatgpt_wrapper import ChatGPT

bot = ChatGPT()
response = asyncio.run(bot.ask("Hello, world!"))
print(response)  # prints the response from chatGPT
```

The say method takes a string argument representing the message to send to ChatGPT, and returns a string representing the response received from ChatGPT.

You may also stream the response as it comes in from ChatGPT in chunks using the `ask_stream` generator.

### Flask API (experimental)

- Run `python chatgpt_wrapper/gpt_api.py --port 5000` (default port is 5000) to start the server
- Test whether it is working using `python -m unittest test/api_test.py`
- See an example of interaction with api in `tests/example_api_call.py`


## Docker (experimental)

Build a image for testing `chatgpt-wrapper` with following commands.

```bash
docker-compose build && docker-compose up -d
docker exec -it chatgpt-wrapper-container /bin/bash -c "chatgpt install"
```

Then, visit http://localhost:6901/vnc.html with password `headless` and login ChatGPT.

Then, turn back to terminal and enjoy the chat!

![chat](https://i.imgur.com/nRlzUzm.png)

## Projects built with chatgpt-wrapper

  - [bookast: ChatGPT Podcast Generator For Books](https://github.com/SamMethnani/bookast)
  - [ChatGPT.el: ChatGPT in Emacs](https://github.com/joshcho/ChatGPT.el)
  - [ChatGPT Reddit Bot](https://github.com/PopDaddyGames/ChatGPT-RedditBot)

## Commit log
- 21/02/2023: v0.3.17
  - Added debug mode (visible browser window).
  - @thehunmonkgroup fixed chat naming.
  - @thehunmonkgroup added !delete command to remove/hide conversations
  - @thehunmonkgroup added --model flag to select model ('default' or 'legacy-paid' or 'legacy-free')
  - @thehunmonkgroup added !editor command to open the current prompt in an editor and send the edited prompt to ChatGPT
  - @thehunmonkgroup added !history command to show the list of the last 20 conversations
  - @NatLee added **docker** support
- 17/02/2023: v0.3.16
  - Ability to open **multiple sessions in parallel**.
  - Code now works with **ChatGPT Plus** subscription.
- 14/02/2023: v0.3.15 - Updated model to text-davinci-002-render-sha (turbo model)
- 14/02/2023: v0.3.11
  - Fixed many bugs with installation. Code is refactored.
  - Now able to use the python wrapper with a **proxy**.
- 18/01/2023: v0.3.8 - Commands now are run only using !. For instance to enable read mode (for copy-paste and long prompts) you need to write now `!read` instead of `read`. This is to avoid conflicts with the chatgpt prompts. Fixed timeout issue.
- 17/01/2023: v0.3.7 - Added timeout to `ask` method to prevent hanging. Fixed return to terminal breakdown. Streaming output now is activated by default.

## Contributing

We welcome contributions to ChatGPT Wrapper! If you have an idea for a new feature or have found a bug, please open an issue on the GitHub repository.

## License

This project is licensed under the MIT License - see the LICENSE file for details.


## Acknowledgments

- This project is a modification from [Taranjeet](https://github.com/taranjeet/chatgpt-api) code which is a modification of [Daniel Gross](https://github.com/danielgross/whatsapp-gpt) code.

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=mmabrouk/chatgpt-wrapper&type=Date)](https://star-history.com/#mmabrouk/chatgpt-wrapper&Date)

## Fund my ChatGPT Plus subscription :)
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/mmabrouk)
