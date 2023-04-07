### v0.8.3 - 07/04/2023

* **Fri Apr 07 2023:** properly set user object in all login scenarios, fixes #260, fixes #262
* **Thu Apr 06 2023:** sync docs

### v0.8.2 - 05/04/2023

* **Wed Apr 05 2023:** enable console/file debugging for --debug arg, print backtrace on command exceptionn when --debug enabled
* **Tue Apr 04 2023:** add shell.history_file config option

### v0.8.1 - 03/04/2023

* **Mon Apr 03 2023:** add support for listing incompatible backends in plugins
* **Mon Apr 03 2023:** abstract prompt prefixing for REPLS, add model prefix for browser backend
* **Mon Apr 03 2023:** add warning message for broken stream interruption on API backend
* **Mon Apr 03 2023:** abstract launching browser context, add warning streaming not working properly on browser backend
* **Sun Apr 02 2023:** support interrupting streaming on API backend
* **Sun Apr 02 2023:** add current datatime util function
* **Sun Apr 02 2023:** convert backends to use langchain custom chat LLM
* **Sun Apr 02 2023:** move LLM class/object creation methods to base backend class
* **Mon Apr 03 2023:** fix ctrl-c/ctrl-d functionality with prompt thread
* **Sat Apr 01 2023:** reorg install section
* **Sat Apr 01 2023:** update doc for backend installation
* **Sat Apr 01 2023:** update sample config
* **Sat Apr 01 2023:** register cleanup function for browser backend

### v0.8.0 - 01/04/2023

#### **:fire_engine:Breaking Changes:fire_engine:**

* All async functionality has been removed
  * Async functionality was determined to be overly complex and buggy for the common use cases in this project.
  * If you were using any async Python modules, switch to their sync version, and consider implementing your own async wrapper or using multithreading if necessary.
* Browser backend and ChatGPT module usage have been deprecated
  * No support will be provided for ChatGPT module usage
  * API backend is now the default
  * Browser backend will remain for now, but may be removed in a future release

#### Commit log

* **Sat Apr 01 2023:** tweak config instructions
* **Sat Apr 01 2023:** update docker entrypoint instructions
* **Sat Apr 01 2023:** deprecate browser backend, ChatGPT module usage, default to API backend
* **Sat Apr 01 2023:** make conversation_data_to_messages() consistent in browser backend
* **Sat Apr 01 2023:** fix set_title(), cleanup get_history() on API backend
* **Sat Apr 01 2023:** add helper func to convert SQLAlchemy objects to plain dicts
* **Sat Apr 01 2023:** dynamically fetch history for older chats on switch/chat/title
* **Fri Mar 31 2023:** completely rip out all async functionality
* **Fri Mar 31 2023:** Add new_conversation to ChatGPT
* **Thu Mar 30 2023:** add interactive arg to launch_backend(), fixes #265
* **Thu Mar 30 2023:** add /copy command, fixes #264
* **Wed Mar 29 2023:** fix broken template tests
* **Wed Mar 29 2023:** add file/directory util functions
* **Tue Mar 28 2023:** add LLM base methods for plugins to leverage

### v0.7.2 - 28/03/2023

* **Tue Mar 28 2023:** add support for .jsonl/.xml to data_query plugin
* **Tue Mar 28 2023:** add config options to shell plugin
* **Tue Mar 28 2023:** small logic improvements to database/data_query plugins
* **Tue Mar 28 2023:** extend /config with edit/section args
* **Mon Mar 27 2023:** add data_query plugin
* **Mon Mar 27 2023:** more robust filename to class conversion
* **Mon Mar 27 2023:** snake_to_class() util function
* **Mon Mar 27 2023:** bump langchain required version
* **Mon Mar 27 2023:** add database plugin
* **Mon Mar 27 2023:** add agent:verbose config value to zap plugin
* **Mon Mar 27 2023:** tighten up prompt template for generating shell commands
* **Mon Mar 27 2023:** allow plugins/users to access configuration for plugins
* **Mon Mar 27 2023:** return None on missing value in config.get()
* **Sun Mar 26 2023:** add unit tests for util functions
* **Sun Mar 26 2023:** reorg docs
* **Sun Mar 26 2023:** convert to Pytest framework
* **Sun Mar 26 2023:** fix SQLAlchemy deprecation warnings

### v0.7.1 - 26/03/2023

* **Sun Mar 26 2023:** per profile playwright sessions for browser backend
* **Sun Mar 26 2023:** no password for test users
* **Sun Mar 26 2023:** clean up errant `console` references, fixes #256
* **Sun Mar 26 2023:** allow custom style for util.print_status_message()

### v0.7.0 - 25/03/2023

#### **:fire_engine:Breaking Changes:fire_engine:**

Lots of file/class/function reorganization:

* Shell usage should be unaffected
* Basic use cases of Python module should be unaffected
* More complex use cases of Python module will probably need code adjustments

* **Sat Mar 25 2023:** abstract template functionality, abstract common functions to util module
* **Sat Mar 25 2023:** user found/not found message helper
* **Sat Mar 25 2023:** reorg file structure, group modules into core/backends

### v0.6.6 - 24/03/2023

* **Fri Mar 24 2023:** add troubleshooting section to docs
* **Fri Mar 24 2023:** add 'chatgpt reinstall' one shot command
* **Thu Mar 23 2023:** add shell plugin

### v0.6.5 - 22/03/2023

* **Wed Mar 22 2023:** inject id into get_conversation() result, add timeout logic for api requests, use for gen_title()
* **Tue Mar 21 2023:** add comment, ctrl-c interrupt generation not working on windows
* **Tue Mar 21 2023:** add support for interrupting streaming by ctrl-c
* **Mon Mar 20 2023:** fix issue writing awesome prompts CSV file
* **Mon Mar 20 2023:** restore ability of /template-edit to create new templates
* **Sun Mar 19 2023:** attempt to fix sync wrapper when loop is always running
* **Sun Mar 19 2023:** add upgrading section to doc

### v0.6.4 - 19/03/2023

* **Sun Mar 19 2023:** add all core plugins to example config
* **Sun Mar 19 2023:** add init file to plugins dir, fixes #239
* **Sun Mar 19 2023:** add langchain dependency
* **Sun Mar 19 2023:** add doc for current core plugins
* **Sun Mar 19 2023:** add zap plugin

### v0.6.3 - 18/03/2023

* **Sat Mar 18 2023:** clean up template display/workflows
* **Sat Mar 18 2023:** extract description separate from overrides, fixes #238

### v0.6.2 - 18/03/2023

* **Sat Mar 18 2023:** /templates command improvements
* **Sat Mar 18 2023:** fix secondary invocations with browser backend, fixes #236

### v0.6.1 - 17/03/2023

#### **:fire_engine:Breaking Changes:fire_engine:**

The `--config-dir` and `--data-dir` arguments have changed how they interpret locations:

* Both now point to the root `chatgpt-wrapper` directory instead of a profile directory
* Config and data are still stored under `profiles/[profile]` subdirectories inside these directories
* Installations that use the default locations instead of providing CLI arguments for the locations are unaffected
* See the output of `chatgpt config` with no other arguments to see these updates reflected in the `File configuration` section

* **Fri Mar 17 2023:** find version in version.py
* **Fri Mar 17 2023:** doc for template front matter
* **Fri Mar 17 2023:** refactor config/data dir implementation, support non-profile specific templates/plugins dirs **BREAKING CHANGE**
* **Thu Mar 16 2023:** pretty up templates list output
* **Thu Mar 16 2023:** add descriptions to example templates
* **Thu Mar 16 2023:** better formatting of template front matter, use description key from front matter in /templates list
* **Thu Mar 16 2023:** enable debug logging for test scripts
* **Thu Mar 16 2023:** check for running event loop, use if found
* **Thu Mar 16 2023:** clarify how to use the sample config

### v0.6.0 - 16/03/2023

* **Thu Mar 16 2023:** fix crash after initial user creation on api backend
* **Wed Mar 15 2023:** Basic plugin functionality (alpha, subject to change)
* **Wed Mar 15 2023:** improvements to model handling
* **Tue Mar 14 2023:** set new backend model after user edit
* **Tue Mar 14 2023:** add set_model method to API backend, error handling/logging for API requests
* **Tue Mar 14 2023:** bump openai version requirement
* **Tue Mar 14 2023:** Minor bug fix: model option was not used in the wrapper (default option was hardcoded)
* **Tue Mar 14 2023:** added gpt4 model option
* **Tue Mar 14 2023:** move signal handling to base shell class, fixes #226
* **Tue Mar 14 2023:** repl_history file use platform agnostic temp dir, fixes #227
* **Mon Mar 13 2023:** Convert commands from underscore to dash
* **Mon Mar 13 2023:** don't start gen_title thread if title already exists
* **Mon Mar 13 2023:** only add check_same_thread for sqlite connections
* **Sun Feb 26 2023:** added flask to requirements
* **Sun Feb 26 2023:** improvement to docker (speed up in debugging and adding api port)

### v0.5.5 - 13/03/2023

* **Mon Mar 13 2023:** fix threading error with SQLite connections
* **Mon Mar 13 2023:** updates to example config
* **Sun Mar 12 2023:** add note about adding EDITOR env var in Windows
* **Sun Mar 12 2023:** try to get windows editor from env first
* **Sun Mar 12 2023:** add install notes for windows users

### v0.5.4 - 12/03/2023

* **Sun Mar 12 2023:** launch backend after check for config CLI arg
* **Sun Mar 12 2023:** fix ask/ask_stream signatures to support custom titles
* **Sun Mar 12 2023:** add prompt-engineer example
* **Sun Mar 12 2023:** add 'Backend configuration' section to config output
* **Sun Mar 12 2023:** temp workaround for issue #224
* **Sat Mar 11 2023:** allow overriding system message in template front matter
* **Sat Mar 11 2023:** add support for frontmatter in templates

### v0.5.3 - 11/03/2023

* **Sat Mar 11 2023:** add some example templates and API scripts
* **Sat Mar 11 2023:** allow passing custom title to ask/ask_stream in api backend
* **Sat Mar 11 2023:** init defaults for templates
* **Sat Mar 11 2023:** try to discover env editor on osx
* **Sat Mar 11 2023:** template_copy/template_delete commands
* **Sat Mar 11 2023:** kill special sauce for linux editor filetype, no longer needed
* **Fri Mar 10 2023:** ensure self.templates is a list
* **Fri Mar 10 2023:** add link to new video walkthrough
* **Fri Mar 10 2023:** fix markdown filetype for vim syntax highlighting

### v0.5.2 - 09/03/2023

* **Fri Mar 10 2023:** **HOTFIX** for broken templates directory location
* **Fri Mar 10 2023:** indicator for current conversation in /history list
* **Fri Mar 10 2023:** tweak /chat help
* **Fri Mar 10 2023:** set new conversation in API backend on user login
* **Fri Mar 10 2023:** add default_user_id arg to init of API backend
* **Fri Mar 10 2023:** add tests for chatgpt-api Python module
* **Fri Mar 10 2023:** output user id in users list
* **Fri Mar 10 2023:** add utility scripts for commit log and pypi release

### v0.5.1 - 09/03/2023

 - Add completions for many more commands
 - Show/set system message (initial context message for all conversations)
 - System message aliases
 - Template management system. See below for details (alpha, subject to change)
 - Set 'markdown' filetype for editor invocations (supports syntax highlighting)
 - Add built template variables, see below for details
 - Native editor module (removes vipe dependency)

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

## OLDER RELEASES

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
