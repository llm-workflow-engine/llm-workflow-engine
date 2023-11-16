### v0.18.4 - 16/11/2023

* **Thu Nov 16 2023:** exclude example dirs that start w/ an underscore
* **Thu Nov 16 2023:** fix examples plugin to work with non-dev installs

### v0.18.3 - 16/11/2023

* **Thu Nov 16 2023:** upgrade to latest langchain, openai 1.x
* **Thu Nov 16 2023:** add provider_azure_openai_chat to plugins list
* **Thu Nov 16 2023:** lock openai package to legacy version for now
* **Mon Nov 06 2023:** upgrade default model to gpt-3.5-turbo-1106
* **Mon Nov 06 2023:** add new OpenAI provider models dated 1106, default to them in presets
* **Fri Oct 20 2023:** remove zap plugin from plugin list

### v0.18.2 - 21/09/2023

* **Thu Sep 21 2023:** bump langchain to 0.0.298
* **Thu Sep 21 2023:** add debug message for built LLM attributes

### v0.18.1 - 19/09/2023

* **Tue Sep 19 2023:** bump langchain to 0.0.295
* **Sun Sep 10 2023:** integrate Backend/ApiBackend
* **Sun Sep 10 2023:** set max_submission_tokens if provided
* **Sun Sep 10 2023:** remove unused import
* **Sun Sep 10 2023:** lwe_llm fixes: not loading profile config from file, add max_submission tokens
* **Sun Sep 10 2023:** add debug log to request init
* **Sun Sep 10 2023:** remove dead arg for max_submission_tokens()

### v0.18.0 - 09/09/2023

Major rewrite of the ApiBackend for maintainability/testability.

No changes to functionality of the Python module or REPL.

#### Commit log

* **Sat Sep 09 2023:** formatting fixes via black
* **Sat Sep 09 2023:** system tests for ApiBackend template operations
* **Sat Sep 09 2023:** add pytest-datadir plugin
* **Sat Sep 09 2023:** move make_template_file to base test module
* **Sat Sep 09 2023:** add links to test badges
* **Sat Sep 09 2023:** better name for test workflow badge
* **Sat Sep 09 2023:** add test/CodeQL badges
* **Sat Sep 09 2023:** fix more linting errors
* **Sat Sep 09 2023:** fix missing test asserts, B015 linting error
* **Sat Sep 09 2023:** fix B907 linting errors
* **Sat Sep 09 2023:** reformat with black
* **Sat Sep 09 2023:** extend flake8 config, add black config
* **Sat Sep 09 2023:** fix linting errors/warnings
* **Sat Sep 09 2023:** add flake8 config file
* **Sat Sep 09 2023:** remove xclip/xvfbwrapper deps
* **Sat Sep 09 2023:** mock pyperclip for unit tests
* **Sat Sep 09 2023:** turn off testing debug
* **Sat Sep 09 2023:** clean up dependency installation
* **Sat Sep 09 2023:** use Xvfb for clipboard tests
* **Sat Sep 09 2023:** use custom FakeMessagesListChatModel for now
* **Sat Sep 09 2023:** set fake OPENAI_API_KEY for tests
* **Sat Sep 09 2023:** temporary hack to debug Github workflow tests
* **Sat Sep 09 2023:** separate workflow step to install app
* **Sat Sep 09 2023:** switch to development install of package
* **Sat Sep 09 2023:** bump Python version requirement to 3.9 or later
* **Sat Sep 09 2023:** fix python version declaration
* **Sat Sep 09 2023:** update codeQL workflow
* **Sat Sep 09 2023:** remove old workflow
* **Thu Aug 17 2023:** don't pollute base presets
* **Sat Sep 09 2023:** Create python-app.yml
* **Sat Sep 09 2023:** more ApiRequest system tests
* **Fri Sep 08 2023:** add missing API doc
* **Fri Sep 08 2023:** add config for API doc
* **Fri Sep 08 2023:** remove unneeded import
* **Fri Sep 08 2023:** script to count total asserts tests
* **Fri Sep 08 2023:** more ApiRequest system tests
* **Fri Sep 08 2023:** combine ApiBackend system tests, add more.
* **Fri Sep 08 2023:** add second test preset to preset manager
* **Fri Sep 08 2023:** template -> template_manager
* **Fri Sep 08 2023:** fix missing API doc
* **Thu Sep 07 2023:** improve TemplateManager unit tests
* **Thu Sep 07 2023:** clean up util class and tests
* **Thu Sep 07 2023:** add more template/util tests
* **Thu Sep 07 2023:** return filepath from create_file()
* **Thu Sep 07 2023:** polish up system tests
* **Thu Sep 07 2023:** add another ConversationStorageManager integration test
* **Thu Sep 07 2023:** add test support methods for creating conversations/messages
* **Wed Sep 06 2023:** add integration tests for ConversationStorageManager
* **Wed Sep 06 2023:** init defaults
* **Wed Sep 06 2023:** add more integration tests for ApiRequest
* **Wed Sep 06 2023:** more unit tests for ApiRequest
* **Wed Sep 06 2023:** refactor build_llm() into more testable units
* **Wed Sep 06 2023:** add more unit tests for ApiRequest
* **Wed Sep 06 2023:** support function to clean colorized output
* **Wed Sep 06 2023:** move log message
* **Wed Sep 06 2023:** reorganize system/integration tests, add more ApiRequest integration tests
* **Wed Sep 06 2023:** refactor post_response, clean up init defaults
* **Tue Sep 05 2023:** more tests for ApiRequest
* **Tue Sep 05 2023:** clean up docstrings
* **Tue Sep 05 2023:** more ApiRequest tests
* **Tue Sep 05 2023:** update function cache tests for recent changes
* **Tue Sep 05 2023:** pass fake testing functions in function_manager fixture
* **Tue Sep 05 2023:** allow passing additional_functions to function manager
* **Tue Sep 05 2023:** only add string function defs to cache, raise on missing functions for non-messages
* **Tue Sep 05 2023:** refactor expand_functions()
* **Tue Sep 05 2023:** abstract output_chunk_content
* **Tue Sep 05 2023:** raise on post_response errors
* **Mon Sep 04 2023:** use config test fixture in integration tests
* **Mon Sep 04 2023:** more robust setup for config fixture
* **Mon Sep 04 2023:** log when test preset is auto-loaded
* **Mon Sep 04 2023:** leverage FakeMessagesListChatModel for fake LLM provider
* **Mon Sep 04 2023:** load test preset conditionally in preset manager
* **Mon Sep 04 2023:** more unit tests for ApiRequest
* **Mon Sep 04 2023:** clean up log message
* **Mon Sep 04 2023:** move terminate_stream() to request class
* **Sun Sep 03 2023:** more unit tests for ApiRequest/ConversationStorageManager
* **Sat Sep 02 2023:** allow providing custom defaults for default customizations
* **Sat Sep 02 2023:** bump openai package
* **Sat Sep 02 2023:** add backend_options.title_generation.provider, allows passing a custom provider for title generation
* **Sat Sep 02 2023:** use file-based test database for history test
* **Sat Sep 02 2023:** support filepath replacement tokens for database settinng
* **Sat Sep 02 2023:** initialize database from backend
* **Sat Sep 02 2023:** add backend_options.auto_create_first_user config option
* **Sat Sep 02 2023:** refactor database connection/session management to support in-memory SQLite
* **Fri Sep 01 2023:** initial ApiRequest tests
* **Fri Sep 01 2023:** add preset_manager test fixture
* **Fri Sep 01 2023:** pass default preset name, always return tuple for set_request_llm()
* **Fri Sep 01 2023:** allow passing additional presets to preset manager
* **Fri Sep 01 2023:** add get_preset() util function
* **Fri Sep 01 2023:** add docstring
* **Thu Aug 31 2023:** abstract more to base test module
* **Thu Aug 31 2023:** reorganize fixtures and util functions
* **Thu Aug 31 2023:** kill unneeded config file
* **Thu Aug 31 2023:** abstract fixtures to base test file
* **Thu Aug 31 2023:** upgrade langchain to v0.0.278
* **Thu Aug 31 2023:** use FakeListChatModel instead
* **Thu Aug 31 2023:** add provider_fake_llm
* **Thu Aug 31 2023:** support function calls in streaming responses
* **Wed Aug 30 2023:** ignore class for testing
* **Wed Aug 30 2023:** fix deprecation warning
* **Wed Aug 30 2023:** unit tests for tokenmanager class
* **Wed Aug 30 2023:** add FakeBackend for testing
* **Wed Aug 30 2023:** fix request function calls
* **Mon Aug 28 2023:** more FunctionCache tests
* **Mon Aug 28 2023:** unit tests for FunctionCache
* **Mon Aug 28 2023:** fix conditional check for function message
* **Mon Aug 28 2023:** add flake8 config
* **Mon Aug 28 2023:** abstract test config setup to helper module
* **Sat Aug 26 2023:** display template before colleting variables
* **Sat Aug 26 2023:** fixes for non chat models
* **Thu Aug 24 2023:** more token manager and function cache to core
* **Mon Aug 21 2023:** bug fixes, first working LLM reqeust and conversation storage
* **Mon Aug 21 2023:** bugfixes
* **Mon Aug 21 2023:** break out much of API backend into multiple support classes
* **Thu Aug 17 2023:** don't pollute base presets
* **Tue Aug 15 2023:** log step of stripping messages based on max tokens
* **Tue Aug 15 2023:** add backend_options attributes to sample config
* **Tue Aug 15 2023:** first pass to revamp streaming

### v0.17.0 - 07/08/2023

#### **:fire_engine:Breaking Changes:fire_engine:**

Command syntax changes for `/user*`, `/template*`, `/preset*`, `/workflow*`:

* `/user` -> `/user show`
* `/user-[action]` -> `/user [action]`
* `/template` -> `/template show`
* `/template-[action]` -> `/template [action]`
* `/preset-[action]` -> `/preset [action]`
* `/workflow-[action]` -> `/workflow [action]`

#### Commit log

* **Mon Aug 07 2023:** convert /user-* commands to '/user [action]'
* **Mon Aug 07 2023:** convert /workflow-* commands to '/workflow [action]'
* **Sun Aug 06 2023:** convert /preset-* to '/preset [action]'
* **Sun Aug 06 2023:** reference class instance for actions
* **Sun Aug 06 2023:** clean temporary templates, catch template parsing errors
* **Sun Aug 06 2023:** fix template / action_template doc
* **Sun Aug 06 2023:** convert /template-* commands to '/template [action]'

### v0.16.1 - 05/08/2023

* **Sat Aug 05 2023:** rip out langchain monkey patching, switch to using .stream()
* **Sat Aug 05 2023:** add config.properties, '/config config_dir', etc.

### v0.16.0 - 03/08/2023

#### **:fire_engine:Breaking Changes:fire_engine:**

`ApiBackend` `ask()` / `ask_stream()` method signatures changed:

* `title` argument was removed
* `title` key added to `request_overrides` arg

Template `title` declaration syntax changed:

Top level `title` key moved under `request_overrides` key.

#### Commit log

* **Thu Aug 03 2023:** fix function signatures for ask/ask_stream
* **Thu Aug 03 2023:** fix call to run_template_compiled()
* **Thu Aug 03 2023:** backend run_template() should accept template vars
* **Thu Aug 03 2023:** fix order of overrides merge
* **Thu Aug 03 2023:** move title override into request_overrides dict

### v0.15.2 - 02/08/2023

* **Wed Aug 02 2023:** add 'activate_preset' option to request_overrides for templates, allows switching to template-defined preset as default
* **Wed Aug 02 2023:** add example code generator template, generates code based on written spec
* **Wed Aug 02 2023:** tweak example code spec generator template
* **Wed Aug 02 2023:** add example code spec generator template
* **Tue Aug 01 2023:** fix namespace collision for 'description' arguments
* **Mon Jul 31 2023:** fix user directories always using 'default' profile path
* **Mon Jul 31 2023:** rip out unneeded Ansible Runner code

### v0.15.1 - 29/07/2023

* **Sat Jul 29 2023:** fix /template-edit* commands to properly re-parse edited template
* **Fri Jul 28 2023:** add vertex provider plugins to list
* **Wed Jul 26 2023:** /workflow-copy command
* **Tue Jul 25 2023:** bump langchain to 0.0.242
* **Tue Jul 25 2023:** remove unneeded override method
* **Mon Jul 24 2023:** add constants for new/untitled title
* **Sun Jul 23 2023:** relax JSON parsing from strict mode, add some logging for function call/response only returns
* **Sun Jul 23 2023:** add code doc for template manager
* **Sat Jul 22 2023:** add prompt prefix token, kill parent_messsage_id

### v0.15.0 - 17/07/2023

#### **:fire_engine:Breaking Changes:fire_engine:**

The following deprecated items have been removed:

* Browser backend: This backend became to brittle and difficult to support, thus the developers made the decision to remove it. Users should consider switching to the more stable API backend.
* `chatgpt` binary: Use the `lwe` binary instead to start the program

#### Commit log

* **Mon Jul 17 2023:** remove incompatible_backend() from Plugin subclass
* **Mon Jul 17 2023:** remove deprecated browser backend, deprecated legacy command leader, deprecated chatgpt binary
* **Mon Jul 17 2023:** kill API example
* **Mon Jul 17 2023:** enable PDF/ePub builds
* **Mon Jul 17 2023:** add research dir, first paper
* **Sun Jul 16 2023:** numerous doc improvements
* **Sun Jul 16 2023:** shell -> command
* **Sun Jul 16 2023:** update installation video links
* **Sun Jul 16 2023:** add code doc example template
* **Sun Jul 16 2023:** switch to multi-column autocomplete menu
* **Sun Jul 16 2023:** improve config display, add options to output individual sections

### v0.14.4 - 15/07/2023

* **Sat Jul 15 2023:** always append to existing debug log
* **Sat Jul 15 2023:** kill flask API
* **Sat Jul 15 2023:** example workflow, voicemail transcription sentiment analysis
* **Sat Jul 15 2023:** better name ansible module loggers
* **Sat Jul 15 2023:** sort examples in list
* **Sat Jul 15 2023:** add lwe_sqlite_query Ansible module, example SQLite db
* **Sat Jul 15 2023:** add description property to plugins, add /plugins command to list enabled plugins
* **Sat Jul 15 2023:** rename /plugin* commands to /chatgpt-plugin* on browser backend
* **Sat Jul 15 2023:** return failure when no conversation id provided
* **Fri Jul 14 2023:** add more example templates
* **Fri Jul 14 2023:** add exploratory code writing example preset
* **Fri Jul 14 2023:** tweak turbo example preset
* **Fri Jul 14 2023:** add attribution for persona generator workflow
* **Fri Jul 14 2023:** add file summarizer and persona generator example workflows
* **Fri Jul 14 2023:** validate workflow has a runnable format before running
* **Fri Jul 14 2023:** touch up workflow examples, more clear names
* **Fri Jul 14 2023:** doc for API backend
* **Fri Jul 14 2023:** clean up template setup return vals, add backend class doc
* **Fri Jul 14 2023:** add doc for pastebin plugin
* **Fri Jul 14 2023:** util.is_valid_url()
* **Thu Jul 13 2023:** add doc for using LWE with shell pipelines
* **Thu Jul 13 2023:** fix init order in backend
* **Thu Jul 13 2023:** option to install examples on initial install
* **Thu Jul 13 2023:** add intro video links
* **Thu Jul 13 2023:** dynamic reload of REPL after config edit
* **Thu Jul 13 2023:** override preset metadata/model_customizations in templates/requests via request_overrides['preset_overrides'] dict

### v0.14.3 - 12/07/2023

#### **:fire_engine:Breaking Changes:fire_engine:**

Most plugins have been moved to their own repository.

If you have any plugins enabled, you'll need to visit the repository for that plugin and follow the installation instructions.

See here for a list of plugins that moved, and their repository links: https://llm-workflow-engine.readthedocs.io/en/latest/plugins.html#lwe-maintained-plugins

#### Commit log

* **Wed Jul 12 2023:** migrate non-core provider plugins to separate packages
* **Wed Jul 12 2023:** clarify non-core plugins must be installed
* **Wed Jul 12 2023:** migrate shell command plugins to separate packages
* **Wed Jul 12 2023:** do_ -> command_ for command method prefix
* **Wed Jul 12 2023:** fix some broken docs links
* **Wed Jul 12 2023:** switch to Sphinx/RTD documentation

### v0.14.2 - 12/07/2023

* **Wed Jul 12 2023:** add RTD build config
* **Wed Jul 12 2023:** more improvements to Sphinx doc
* **Wed Jul 12 2023:** enable examples plugin by default

### v0.14.1 - 12/07/2023

* **Wed Jul 12 2023:** fix bad variable when stripping out messages over max tokens
* **Tue Jul 11 2023:** more rebranding renames

### v0.14.0 - 11/07/2023

#### ChatGPT Wrapper has been re-branded to LLM Workflow Engine

Currently, all functionality is the same.

#### **:fire_engine:Breaking Changes:fire_engine:**

* Default configuration and data directories have changed
  * A deprecation warning will be thrown on startup if the legacy directories are being used, with instructions on how to migrate to the new default locations.
  * Legacy locations will continue to be supported until at least the next minor point release
* Environment variable names have changed
  * `CHATGPT_WRAPPER_CONFIG_DIR` renamed to `LWE_CONFIG_DIR`
  * `CHATGPT_WRAPPER_CONFIG_PROFILE` renamed to `LWE_CONFIG_PROFILE`
  * `CHATGPT_WRAPPER_DATA_DIR` renamed to `LWE_DATA_DIR`
* Log file locations have changed: `chatgpt` -> `lwe`

#### Commit log

* **Tue Jul 11 2023:** add deprecation warning for chatgpt binary
* **Tue Jul 11 2023:** ChatGPT Wrapper -> LLM Workflow Engine rebranding
* **Tue Jul 11 2023:** throw warning messages for legacy config/data dirs
* **Tue Jul 11 2023:** display max submission tokens in runtime config
* **Tue Jul 11 2023:** fix spelling error
* **Mon Jul 10 2023:** document installing examples
* **Mon Jul 10 2023:** mention more examples in features list
* **Mon Jul 10 2023:** polish functions doc
* **Sun Jul 09 2023:** flesh out workflow doc
* **Sun Jul 09 2023:** examples plugin, installs example config files, plus more example files

### v0.13.2 - 08/07/2023

* **Sat Jul 08 2023:** support running workflows from CLI args, --workflow/--workflow-args
* **Sat Jul 08 2023:** clean up display of workflows in /workflows command
* **Sat Jul 08 2023:** bump textract version
* **Sat Jul 08 2023:** add max_length param to text_extractor module
* **Wed Jun 28 2023:** update docker base container, remove VNC access, API backend only
* **Wed Jun 28 2023:** remove deprecated openai chat models

### v0.13.1 - 27/06/2023

* **Tue Jun 27 2023:** remove outdated openai chat models
* **Tue Jun 27 2023:** touch up new Sphinx documentation
* **Tue Jun 27 2023:** update doc for using GPT-4 in Python module
* **Tue Jun 27 2023:** prevent function recursion when functions are forced (for now)
* **Tue Jun 27 2023:** add function_call to model_kwargs
* **Tue Jun 27 2023:** bump langchain dep
* **Tue Jun 27 2023:** add return_only property to API backend, suppresses console output
* **Tue Jun 27 2023:** escape jinja syntax in system message
* **Tue Jun 27 2023:** manage override preset on override_llm invocation
* **Tue Jun 27 2023:** tighten rules for workflow spec generation template
* **Tue Jun 27 2023:** fine-tune workflow spec/generation templates
* **Mon Jun 26 2023:** add doc for how it works, installation, initial setup, presets, python module
* **Mon Jun 26 2023:** display playbook descriptions in /workflows command
* **Mon Jun 26 2023:** add descriptions for system presets
* **Mon Jun 26 2023:** tweak installation instructions
* **Mon Jun 26 2023:** autosection labels, pygments highlighting
* **Mon Jun 26 2023:** theme config, logo, index/installation pages
* **Mon Jun 26 2023:** fix syntax for RST formatting
* **Sun Jun 25 2023:** Sphinx documentation scaffolding
* **Sun Jun 25 2023:** require at least version 0.20.1 of docutils
* **Sun Jun 25 2023:** add support for langchain tools as functions
* **Sun Jun 25 2023:** add remove_prefix util function

### v0.13.0 - 25/06/2023

* **Sun Jun 25 2023:** documentation for OpenAI functions
* **Sun Jun 25 2023:** add function descriptions to /functions command
* **Sun Jun 25 2023:** allow recursive function calling for return_on_function_response
* **Sun Jun 25 2023:** add core test function
* **Sun Jun 25 2023:** better traceback from function instance loading errors
* **Sun Jun 25 2023:** add missing docutils requirement
* **Sun Jun 25 2023:** bump openai dependency
* **Sun Jun 25 2023:** roll custom textract, current package not well maintained
* **Sat Jun 24 2023:** build open function spec from function type hints and doc if .config.yaml file is not provided
* **Sat Jun 24 2023:** move more template logic into template manager class
* **Fri Jun 23 2023:** prevent duplicate loggers
* **Fri Jun 23 2023:** dynamically check/build function definitions for LLM calls and token counting
* **Thu Jun 22 2023:** pass messages around as dicts, transform at edges
* **Thu Jun 22 2023:** allow message_metadata to be NULL
* **Thu Jun 22 2023:** DRY message objects
* **Wed Jun 21 2023:** bump langchain dep, clean up some monkey patching
* **Wed Jun 21 2023:** multi-function processing with final LLM output
* **Tue Jun 20 2023:** only expand functions once
* **Tue Jun 20 2023:** refactor functions to be callable classes, default YAML config in separate file
* **Sun Jun 18 2023:** fix monkey patch for langchain FunctionMessage
* **Sun Jun 18 2023:** listing/running functions, allow returning directly after function calls
* **Sun Jun 18 2023:** sort system message alias list in /system-messages
* **Sun Jun 18 2023:** change checkmark indicator to green circle
* **Sun Jun 18 2023:** add post revision creation instructions for re-importing data
* **Sun Jun 18 2023:** script to automate creating new schema revisions
* **Sun Jun 18 2023:** abstract determining message content from message type
* **Sat Jun 17 2023:** filter full message dict before sending to LLM
* **Sat Jun 17 2023:** add message_metadata to messages table, refactoring in prep for full functions support
* **Sat Jun 17 2023:** clean up /config display, add database entry to file section
* **Sat Jun 17 2023:** add cli args for template/plugin/function/workflow/preset dirs, clean up cli doc
* **Fri Jun 16 2023:** include header in ansible module doc, provide full/summary modes
* **Fri Jun 16 2023:** limit length of title generation message
* **Fri Jun 16 2023:** util functions to extract Ansible doc to Markdown
* **Thu Jun 15 2023:** properly update updated_time for conversations on new message
* **Thu Jun 15 2023:** store provider/model/preset per message, add message_type field
* **Thu Jun 15 2023:** expose LWE_SCHEMA_MIGRATION_SQLALCHEMY_URL environment variable for autogenerating migrations
* **Thu Jun 15 2023:** loosen sqlalchemy requirements
* **Thu Jun 15 2023:** add post_response method, for actions after response has been received

### v0.12.3 - 25/06/2023

* **Sun Jun 25 2023:** roll custom textract, current package not well maintained
* **Sun Jun 25 2023:** bump openai dependency

### v0.12.2 - 15/06/2023

#### **:fire_engine:Breaking Changes:fire_engine:**

GPT-4 models are currently broken in the browser backend, due to increased 'anti-bot' security measures implemented by OpenAI on
chat.openai.com

If you'd like to help fix this issue, see https://github.com/llm-workflow-engine/llm-workflow-engine/issues/311

#### Commit log

* **Thu Jun 15 2023:** add warning, GPT-4 models broken on browser backend
* **Wed Jun 14 2023:** add function manager
* **Wed Jun 14 2023:** add /preset-edit command, to edit existing presets, ensure load_preset() succeeds
* **Wed Jun 14 2023:** add creative writer system message, use in system preset
* **Wed Jun 14 2023:** init_system_message when init_provider, missing conversation preset
* **Wed Jun 14 2023:** openai functions: ability to configure functions in presets, store assistant function reply
* **Wed Jun 14 2023:** add system message to chatbot/creative writing presets
* **Wed Jun 14 2023:** pass through provider customization when a key's value is None, skip completions
* **Wed Jun 14 2023:** empty user metadata field in /preset-save removes field from preset
* **Tue Jun 13 2023:** add workflow review template
* **Tue Jun 13 2023:** add new openai chat models released 0613

### v0.12.1 - 13/06/2023

* **Tue Jun 13 2023:** monkey patch / version lock langchain with stream interruption fixes, fixes #274, fixes #180

### v0.12.0 - 13/06/2023

#### **:fire_engine:Breaking Changes:fire_engine:**

* The base module namespace has been changed from `chatgpt_wrapper` to `lwe` in preparation for a re-branding.
  This affects all uses of the Python module, the change is straightforward:

  OLD:

  ```python
  from chatgpt_wrapper import ApiBackend
  from chatgpt_wrapper.core.config import Config
  ```

  NEW:
  ```python
  from lwe import ApiBackend
  from lwe.core.config import Config
  ```
* For packaged plugins, the plugin namespace has changed from `chatgpt_wrapper` to `lwe`.

### v0.11.7 - 12/06/2023

* **Mon Jun 12 2023:** delete confirmation for presets/workflows
* **Mon Jun 12 2023:** allow copying system templates to user directories
* **Mon Jun 12 2023:** allow LWE_ environment variable overrides of templates/plugins/presets/workflows dirs
* **Mon Jun 12 2023:** configuration overrides for user templates/plugins/presets/workflows dirs
* **Sun Jun 11 2023:** doc and examples for lwe_input action plugin
* **Sun Jun 11 2023:** output workflow dirs for /config
* **Sun Jun 11 2023:** add remaining customization_config values to openai providers
* **Sun Jun 11 2023:** don't include dict values as empty completions

### v0.11.6 - 10/06/2023

* **Sat Jun 10 2023:** /preset-show defaults to current preset
* **Sat Jun 10 2023:** fix api temperature check example
* **Sat Jun 10 2023:** allow storing system message with a preset, allow storing non-aliased system messages
* **Sat Jun 10 2023:** reset provider customizations loading a provider
* **Sat Jun 10 2023:** upgrade presets schema to be more robust
* **Sat Jun 10 2023:** pass config/data dirs to schema updater config, generalize message
* **Fri Jun 09 2023:** better output for example social media workflow
* **Fri Jun 09 2023:** better status message for opening editor
* **Fri Jun 09 2023:** replace pause with lwe_input
* **Thu Jun 08 2023:** cleaner infinite task workflow approach
* **Thu Jun 08 2023:** llm-iterative-tasks workflow, infinite loop until user exits

### v0.11.5 - 08/06/2023

* **Thu Jun 08 2023:** rename lwe module to lwe_llm module
* **Thu Jun 08 2023:** add custom lwe_input action plugin, with editor support
* **Thu Jun 08 2023:** convert text_extractor to textract, many more extensions supported
* **Thu Jun 08 2023:** html_extractor -> text_extractor, add PDF support, scrub non-UTF-8 in text files

### v0.11.4 - 08/06/2023

* **Thu Jun 08 2023:** don't re-init provider on new conversation
* **Thu Jun 08 2023:** best guess cast random dict model customizations, recurse dicts when setting customization values
* **Thu Jun 08 2023:** rebuild completions on /preset-load, activate preset on /preset-save, init default provider when deleting active preset
* **Wed Jun 07 2023:** rebranding writeup.
* **Wed Jun 07 2023:** example workflow for generating and posting social media content
* **Tue Jun 06 2023:** example workflow: summarize HTML page
* **Tue Jun 06 2023:** add html_extractor workflow module
* **Tue Jun 06 2023:** syntax cleanup

### v0.11.3 - 06/06/2023

* **Tue Jun 06 2023:** add multi-workflow example
* **Tue Jun 06 2023:** fix passing args to workflows
* **Tue Jun 06 2023:** replace ansible-runner with ansible-playbook subprocess
* **Tue Jun 06 2023:** kill dead file
* **Tue Jun 06 2023:** clean up prompt formatting

### v0.11.2 - 05/06/2023

* **Mon Jun 05 2023:** add template/variable support for workflows
* **Mon Jun 05 2023:** tweak lwe ansible module exit data
* **Mon Jun 05 2023:** move template manager instantiation to backend
* **Mon Jun 05 2023:** document running workflows directly with ansible-playbook
* **Mon Jun 05 2023:** add default ansible callback config

### v0.11.1 - 05/06/2023

* **Mon Jun 05 2023:** fix missing workflow directories

### v0.11.0 - 04/06/2023

* **Sun Jun 04 2023:** fixes to workflow CLI help
* **Sun Jun 04 2023:** add documentation for workflows
* **Sun Jun 04 2023:** flesh out lwe doc
* **Sun Jun 04 2023:** migrate workflow from plugin to API backend
* **Sun Jun 04 2023:** add workflow show/edit/delete commands
* **Sun Jun 04 2023:** output YAML in workflow runs
* **Sun Jun 04 2023:** allow both user IDs and usernames in user arg to lwe module
* **Sun Jun 04 2023:** refine and comment example workflows
* **Sun Jun 04 2023:** save conversation ID in lwe results dict
* **Sun Jun 04 2023:** convert lwe ansible module to LWE API backend
* **Sun Jun 04 2023:** add backend_options.default_user, backend_options.default_conversation_id to config, backend loading of default user/conversation
* **Sat Jun 03 2023:** provide default file for extravars
* **Sat Jun 03 2023:** support passing workflow args in /workflow-run
* **Sat Jun 03 2023:** include more example workflows, mechanism for collecting var_prompt variables in playbooks
* **Sat Jun 03 2023:** initial ansible playbook integration for workflows
* **Sun May 28 2023:** bold styling for user prompt
* **Sun May 28 2023:** color-code role labels in /chat output
* **Mon May 22 2023:** very basic workflow manager and workflow base class, with test workflow in Prefect

### v0.10.7 - 27/05/2023

* **Sat May 27 2023:** allow setting system message alias in config (model.default_system_message) or CLI (-s/--system-message)
* **Sat May 27 2023:** read both extra params and input file for one-shot mode
* **Thu May 25 2023:** add -i/--input-file argument
* **Mon May 22 2023:** restore SQLAlchemy compat with 1.4.x
* **Thu May 18 2023:** kill lingering deprecated chatgpt-browser/chatgpt-api

### v0.10.6 - 18/05/2023

* **Thu May 18 2023:** fix streaming when overriding a preset in templates

### v0.10.5 - 17/05/2023

* **Wed May 17 2023:** add doc for browser backend with web browser support
* **Wed May 17 2023:** add support for ChatGPT with browsing (alpha, browser backend only)

### v0.10.4 - 15/05/2023

* **Mon May 15 2023:** fix broken streaming, clean up can/should stream logic, fixes #303

### v0.10.3 - 15/05/2023

* **Mon May 15 2023:** clean up alembic config process
* **Mon May 15 2023:** add util function to get directory of any file
* **Mon May 15 2023:** fix missing alembic files

### v0.10.2 - 14/05/2023

* **Sun May 14 2023:** fix missing __init__ file for schema dir

### v0.10.1 - 13/05/2023

#### **:fire_engine:Deprecations:fire_engine:**

* Configuration `backend:` settings have changed values
  * `chatgpt-api` is now `api`
  * `chatgpt-browser` is now `browser`

#### Commit log

* **Sat May 13 2023:** fix some message composition and streaming bugs
* **Sat May 13 2023:** fix default args to prevent mutable default args bugs
* **Sat May 13 2023:** update backend config names, add deprecation warning for old names

### v0.10.0 - 13/05/2023

#### **:fire_engine:Breaking Changes:fire_engine:**

This version performs operations on the database that stores users/conversations/messages.
**Please read the the upgrade warnings at https://github.com/mmabrouk/chatgpt-wrapper#upgrading prior to running the upgrade!**

#### New features

* Plugin support for browser backend
* Database schema upgrade system
* Per user default presets
* Switching conversations loads original preset or provider/module used when conversation was created

#### Commit log

* **Sat May 13 2023:** document per-user default presets
* **Sat May 13 2023:** fix random bugs with streaming across providers
* **Sat May 13 2023:** document plugin support
* **Sat May 13 2023:** /plugin-enable and /plugin-disable commands, dynamically add/remove plugins
* **Sat May 13 2023:** add /enabled-plugins command
* **Sat May 13 2023:** underscore commands in help command substitution
* **Sat May 13 2023:** add plugin support to browser backend, /plugins list command
* **Sat May 13 2023:** add database upgrade warnings to README
* **Sat May 13 2023:** add  prompt replacement token, indicator for active preset in /presets command
* **Sat May 13 2023:** schema upgrade, store provider and preset for conversation, use when re-loading conversations
* **Sat May 13 2023:** exit on upgrade error
* **Sat May 13 2023:** improve stream logging
* **Sat May 13 2023:** working user default presets
* **Fri May 12 2023:** improve display/management of system message aliases
* **Thu May 11 2023:** schema upgrade, default_model -> default_preset for users
* **Thu May 11 2023:** database schema upgrade system using alembic
* **Wed May 10 2023:** clarify doc for presets
* **Tue May 09 2023:** timeout for trying to retrieve awesome prompts

### v0.9.0 - 08/05/2023

This is a substantial rewrite to add support for multiple providers and management of preset configurations.

New features are documented in the README.

#### **:fire_engine:Breaking Changes:fire_engine:**

##### Configuration

* Removed the following values from `shell.prompt_prefix`:
  * `$TOP_P`
  * `$PRESENCE_PENALTY`
  * `$FREQUENCY_PENALTY`
* Removed `chat.model` configuration setting.
* Removed `chat.model_customizations` configuration setting.
* Added a new `model` configuration hash, with the following new attributes:
  * `default_preset`
* Moved `chat.model_customizations.system_message` configuration setting to `model.system_message`
* Moved `chat.streaming` configuration setting to `model.streaming`

##### CLI use

* `--model` command line argument has been removed
* `--preset` command line argument has been added
* Saving/editing a default model per user in the API backend has been removed
* `/model` command has been rewritten. See `/help model` for more information
* Removed the following commands:
  * `/model-temperature`: Now set under `/model temperature`
  * `/model-top-p`: Now set under `/model model_kwargs`
  * `/model-presence-penalty`: Now set under `/model model_kwargs`
  * `/model-frequency-penalty`: Now set under `/model model_kwargs`
* Renamed the following commands:
  * `/model-system-message` to `/system-message`

##### Templates

* Special `model_customizations` variable has been renamed to `request_overrides`, and functionality has changed. See the `Templates` section in the README for more info.

##### Python module use

* API backend modules location changed to `backends/api`
* API backend file location changed to `backends/api/backend.py`
* API backend class `OpenAIAPI` renamed to `ApiBackend`
* Removed the following abstract methods from the base `Backend` class:
  * `get_backend_name`
  * `set_available_models`
* Added the following abstract methods to the base `Backend` class:
  * `set_override_llm`

#### Commit log

* **Mon May 08 2023:** update documentation for presets/providers
* **Mon May 08 2023:** add /providers command to list providers, sort presets/templates
* **Mon May 08 2023:** update example config
* **Mon May 08 2023:** enhance browser backend test, add wait arg
* **Mon May 08 2023:** convert all direct API calls in browser backend to use injected XHR requests
* **Mon May 08 2023:** function/var renames for clarity
* **Mon May 08 2023:** update pip package description
* **Mon May 08 2023:** rename classes for clarity
* **Sun May 07 2023:** add commented list of openai codex models
* **Sun May 07 2023:** add huggingface_hub provider
* **Sun May 07 2023:** add openai provider
* **Sun May 07 2023:** add AI21 provider
* **Sun May 07 2023:** update CLI args, remove model, add preset
* **Sun May 07 2023:** fix streaming on override LLM
* **Sun May 07 2023:** custom LLM override functionality, allow override using preset in templates
* **Sun May 07 2023:** include name in preset metadata
* **Sun May 07 2023:** re-add max-submission-tokens, abstract for multiple providers, enhance error message for get_set_backend_setting(), add get_capability() method to provider class, discover provider from model, use when switching conversations, remove errant streaming capabilitiy from cohere provider
* **Sat May 06 2023:** update sample config
* **Sat May 06 2023:** move preset_manager to backend, refactor init model to init with default preset, remove dead constants, model_customizations -> request_overrides, refactor config setting locations
* **Sat May 06 2023:** strings instead of arrays for non-chat LLM messages
* **Sat May 06 2023:** upgrade langchain/sqlalchemy, cohere dep
* **Sat May 06 2023:** abstract title generation, message preparation/extraction
* **Sat May 06 2023:** REPL stream references backend stream setting
* **Fri May 05 2023:** should_stream() for backend, look at streaming setting directly
* **Thu May 04 2023:** add get_customizations() method, scrubs metadata
* **Thu May 04 2023:** working presets, fix streaming in API backend
* **Wed May 03 2023:** add cohere plugin
* **Wed May 03 2023:** rebuild completions on provider change, start abstracting model property name
* **Wed May 03 2023:** /provider command to switch providers
* **Wed May 03 2023:** more robust provider loading
* **Wed May 03 2023:** add PROVIDER_PREFIX constant
* **Wed May 03 2023:** display/full name management for providers
* **Wed May 03 2023:** refactor model handling, get/set models
* **Wed May 03 2023:** restrict langchain version, fixes #296
* **Tue Apr 25 2023:** check for and close browser page in cleanup()
* **Mon Apr 24 2023:** basic working API backend implementation with ChatOpenAI
* **Sun Apr 23 2023:** clarify instructions for GPT-4 use
* **Sat Apr 22 2023:** check for existing browser pages before closing context, add more debugging to cleanp()
* **Thu Apr 13 2023:** rip out model specific commands, refactor do_model, fix model completions
* **Thu Apr 13 2023:** loosen up timestamp string for conversion, fixes #287
* **Wed Apr 12 2023:** move llm creation into provider class, move browser backend provider to plugin
* **Wed Apr 12 2023:** initial preset manager
* **Tue Apr 11 2023:** make api key/org private
* **Tue Apr 11 2023:** PresetValue class, functionality to set model customizations
* **Tue Apr 11 2023:** Get Docker container working, clarify documentation, fixes #268, fixes #276, fixes #281
* **Tue Apr 11 2023:** clean up browser integration test
* **Tue Apr 11 2023:** speed up zap plugin loading
* **Mon Apr 10 2023:** move plugin manager instantiation to backends
* **Mon Apr 10 2023:** support passing list of additional plugins to plugin manager
* **Mon Apr 10 2023:** add provider base class, move chat_openai provider plugin
* **Sat Apr 08 2023:** initial provider manager implementation

### v0.8.4 - 13/04/2023

* **Thu Apr 13 2023:** loosen up timestamp string for conversion, fixes #287
* **Tue Apr 11 2023:** Get Docker container working, clarify documentation, fixes #268, fixes #276, fixes #281
* **Tue Apr 11 2023:** clean up browser integration test
* **Sat Apr 08 2023:** clarify API backed model is set per user, fixes #283
* **Sat Apr 08 2023:** provide empty config if config file is empty, fixes #282
* **Fri Apr 07 2023:** enable echo plugin by default, remove awesome plugin as default
* **Fri Apr 07 2023:** move test plugin to echo
* **Fri Apr 07 2023:** fix syntax error in setup script, fixes #280
* **Fri Apr 07 2023:** add support for plugin packages

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
