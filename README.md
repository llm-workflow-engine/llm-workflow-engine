<h1><p align="center">:candy:ChatGPT Wrapper:candy:</p></h1>

<p align="center">ChatGPT Wrapper is an open-source unofficial <b>Power CLI</b>, <b>Python API</b> and <b>Flask API</b> that lets you interact programmatically with ChatGPT.</p>

## Highlights

🤖 **Programmable ChatGPT**. The ChatGPT Wrapper lets you use the powerful ChatGPT bot in your _Python scripts_ or on the _command line_, making it easy to leverage its functionality into your projects.

💬 **Runs in Shell**. You can call and interact with ChatGPT in the terminal.

💻  **Supports official ChatGPT API**. Make API calls directly to the OpenAI ChatGPT endpoint.

🐍 **Python API**. The ChatGPT Wrapper is a Python library that lets you use ChatGPT in your Python scripts.

🐳 **Docker image**. The ChatGPT Wrapper is also available as a docker image. (experimental)

:test_tube: **Flask API**. You can use the ChatGPT Wrapper as an API. (experimental)

## Release Notes

### v0.5.1 - 09/03/2023

 - Add completions for many more commands
 - Show/set system message (initial context message for all conversations)
 - System message aliases
 - Template management system. See below for details (alpha, subject to change)
 - Set 'markdown' filetype for editor invocations (supports syntax highlighting)
 - Add built template variables, see below for details

### v0.5.0 - 08/03/2023

#### **:fire_engine:Breaking Changes:fire_engine:**

 - The return values for the public methods of the `ChatGPT`/`AsyncChatGPT` classes have changed, they are now tuple with the following values:
   - `success`: Boolean, True if the operation succeeded, False if the operation failed.
   - `data`: Object, the data the command generated.
   - `message`: Human-readable message about the outcome of the operation.

 - Introduced the concept of multiple 'backends' -- see below for the currently supported ones
 - Added the 'chatgpt-api' backend, communicates via the official OpenAI REST endpoint for ChatGPT
   - Basic multi-user support (admin party at CLI)
   - Data stored in a database (SQLite by default, any configurable in SQLAlchemy allowed)
   - Allows full model customiztion
   - Numerous new shell commands and enhancements

### v0.4.3 - 03/03/2023

#### **:fire_engine:Breaking Changes:fire_engine:**

 - ChatGPT/AsyncChatGPT classes have changed how they receive configuration values, be sure to investigate the new function signatues for their __init__() and create() methods.

### What is new?

 - [New configuration system](/config.sample.yaml)
 - Added '/config' command

### v0.4.2 - 01/03/2023

 - Fix broken `ChatGPT` sync class
 - Removed nest_asyncio dependency
 - Convert CLI to use `AsyncChatGPT` class
 - Initial implementation of stop generating text response

### v0.4.1 - 28/02/2023

- REVERT BREAKING CHANGE: Asyncio module requirement _removed_ from usage of ChatGPT class, it is now a sync wrapper around the async class

### v0.4.0 - 27/02/2023

#### **:fire_engine:Breaking Changes:fire_engine:**

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

- **_Migrated to async Playwright_**
- **_Initial API in Flask_** (see [How to use the API](#flask-api))
- Added tab completion for commands
- Added '/tmp' volume for saving Playwright session
- Added CI and CodeQL workflows
- Added simple developer debug module
- Improved session refreshing (**_/session now works!_**)
- Migrated to Prompt Toolkit

[See commit log for previous updates](#commit-log)

## How it works

Run an interactive CLI in the terminal:

![kod](https://user-images.githubusercontent.com/4510758/212907070-602d61fe-708d-4a39-aaa2-0e84fcf88dcf.png)

Or just get a quick response for one question:

![kod(1)](https://user-images.githubusercontent.com/4510758/212906773-666be6fe-90e1-4f5e-b962-7748143bd744.png)

See below for details on using ChatGPT as an API from Python.

## Requirements

To use this repository, you need `setuptools` installed. You can install it using `pip install setuptools`. Make sure that you have the last version of pip: `pip install --upgrade pip`

To use the 'chatgpt-api' backend, you need a database backend (SQLite by default, any configurable in SQLAlchemy allowed).

## Installation

### Code

#### From packages

Install the latest version of this software directly from github with pip:

```bash
pip install git+https://github.com/mmabrouk/chatgpt-wrapper
```
#### From source (recommended for development)

* Install the latest version of this software directly from git:
  ```bash
  git clone https://github.com/mmabrouk/chatgpt-wrapper.git
  ```
* Install the the development package:
  ```bash
  cd chatgpt-wrapper
  pip install -e .
  ```

### Backend

The wrapper works with several differnt backends to connect to the ChatGPT models, and installation is different for each backend.

#### Playwright (browser-based)

* Pros:
  * Free or paid version available (as of this writing)
  * Fairly easy to set up for non-technical users
* Cons:
  * Slow (runs a full browser session)
  * Clunky authentication method
  * No model customizations
  * Third party controls your data

Install a browser in playwright (if you haven't already). The program will use firefox by default.

```
playwright install firefox
```

Start up the program in `install` mode:

```bash
chatgpt install
```

This opens up a browser window. Log in to ChatGPT in the browser window, walk through all the intro screens, then exit program.

```bash
1> /exit
```

Restart the program without the `install` parameter to begin using it.

```bash
chatgpt
```

#### API (REST-based)

* Pros:
  * Fast (many operations run locally for speed)
  * Simple API authentication
  * Full model customizations
  * You control your data
* Cons:
  * Only paid version available (as of this writing)
  * More commplex setup suitable for technical users

Grab an API key from [https://platform.openai.com/account/api-keys](https://platform.openai.com/account/api-keys)

Export the key into your local environment:

```bash
export OPENAI_API_KEY=<API_KEY>
```

Run the program with the 'config' command:

```bash
chatgpt config
```

This will show all the current configuration settings, the most important ones for installation are:

* **Config dir:** Where configuration files are stored
* **Current profile:** (shown in the 'Profile configuration' section)
* **Config file:** The configuration file current being used
* **Data dir:** The data storage directory

Find the 'Config file' setting, and copy the [config.sample.yaml](/config.sample.yaml) there:

 ```bash
mkdir -p ~/.config/chatgpt-wrapper/profiles/default
cp config.sample.yaml ~/.config/chatgpt-wrapper/profiles/default/config.yaml
```

Then edit the settings in that file to taste.  You'll want to make sure `backend` is set to `chatgpt-api` in order to use the API.

##### Database configuration

The API backend requires a database server to store conversation data. The wrapper leverages [SQLAlchemy](https://www.sqlalchemy.org/) for this.

The simplest supported database is SQLite (which is already installed on most modern operating systems), but you can use any database that is supported by SQLAlchemy.

Check the `database` setting from the `config` command above, which will show you the currently configured connection string for a default SQLite database.

If you're happy with that setting, nothing else needs to be done -- the database will be created automatically in that location when you run the program.

##### Initial user creation and login

Once the database is configured, run the program with no arguments:

```bash
chatgpt
```

It will recognize no users have been created, and prompt you to create the first user:

* Username: Required, no spaces or special characters
* Email: Optional
* Password: Optional, if not provided the user can log in without a password

Once the user is created, execute the `/login` command with the username:

```bash
/login [username]
```

Once you're logged in, you have full access to all commands.

**IMPORTANT NOTE:** The user authorization system from the command line is 'admin party' -- meaning every logged in user has admin privileges, including editing and deleting other users.


## Configuration

From a running `chatgpt` instance, execute `/config` to view the current configuration.

The output will show the location of the configuration directory, the name of
the configuration file (called a 'profile'), and the current configuration.

Configuration is optional, default values will be used if no configuration profile is
provided. The default configuation settings can be seen in
[config.sample.yaml](/config.sample.yaml) -- the file is commented with descriptions 
of the settings.

*NOTE:* Not all settings are available on all backends. See the example config for more information.

Command line arguments overrride custom configuration settings, which override default
configuration settings.

## Templates (alpha, subject to change)

The wrapper comes with a full template management system.

Templates allow storing text in template files, and quickly leveraging the contents as your user input.

Features:

 * Per-profile templates
 * Create/edit templates
 * `{{ variable }}` syntax substitution
 * Five different workflows for collecting variable values, editing, and running

See the various `/help template` commands for more information.

### Template builtin variables

The wrapper exposes some builtin variables that can be used in templates:

 * `{{ clipboard }}` - Insert the contents of the clipboard

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
from chatgpt_wrapper import ChatGPT

bot = ChatGPT()
success, response, message = bot.ask("Hello, world!")
if success:
    print(response)
else:
    raise RuntimeError(message)
```

The say method takes a string argument representing the message to send to ChatGPT, and returns a string representing the response received from ChatGPT.

You may also stream the response as it comes in from ChatGPT in chunks using the `ask_stream` generator.

To pass custom configuration to ChatGPT, use the Config class:

```python
from chatgpt_wrapper import ChatGPT
from chatgpt_wrapper.config import Config

config = Config()
config.set('browser.debug', True)
bot = ChatGPT(config)
success, response, message = bot.ask("Hello, world!")
if success:
    print(response)
else:
    raise RuntimeError(message)
```

### Flask API (experimental)

- Run `python chatgpt_wrapper/gpt_api.py --port 5000` (default port is 5000) to start the server
- Test whether it is working using `python -m unittest tests/api_test.py`
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
  - @thehunmonkgroup added !delete command to remove/hide conversations.
  - @thehunmonkgroup added --model flag to select model ('default' or 'legacy-paid' or 'legacy-free').
  - @thehunmonkgroup added !editor command to open the current prompt in an editor and send the edited prompt to ChatGPT.
  - @thehunmonkgroup added !history command to show the list of the last 20 conversations.
  - @NatLee added **docker** support.
- 17/02/2023: v0.3.16
  - Ability to open **multiple sessions in parallel**.
  - Code now works with **ChatGPT Plus** subscription.
- 14/02/2023: v0.3.15 - Updated model to text-davinci-002-render-sha (turbo model).
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
