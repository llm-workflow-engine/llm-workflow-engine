# Constants used across the modules are stored here.

import os
import tempfile

PROVIDER_PREFIX = "provider_"
PROVIDER_PRIVATE_CUSTOMIZATION_KEYS = [
    "tools",
    "tool_choice",
]

# Backend specific constants
API_BACKEND_DEFAULT_MODEL = "gpt-4o-mini"

SYSTEM_MESSAGE_DEFAULT = "You are a helpful assistant."
SYSTEM_MESSAGE_PROGRAMMER = (
    "You are an expert programmer, who responds to questions with brief examples in code."
)
SYSTEM_MESSAGE_CREATIVE_WRITER = "You are a creative writing assistant."
DEFAULT_TITLE_GENERATION_SYSTEM_PROMPT = "You write short 3-5 word titles for any content"
DEFAULT_TITLE_GENERATION_USER_PROMPT = "Write a title for this content:"
TITLE_GENERATION_MAX_CHARACTERS = 1500

# Titles.
NEW_CONVERSATION_TITLE = "[New Conversation]"
UNTITLED_CONVERSATION = "[Untitled]"
NO_TITLE_TEXT = "No title"
SHORT_TITLE_LENGTH = 30

OPEN_AI_MAX_TOKENS = 4096
OPEN_AI_MIN_SUBMISSION_TOKENS = 1
OPEN_AI_DEFAULT_MAX_SUBMISSION_TOKENS = 4000

# Config specific constants.
DEFAULT_PROFILE = "default"
DEFAULT_CONFIG_DIR = "llm-workflow-engine"
LEGACY_DEFAULT_CONFIG_DIR = "chatgpt-wrapper"
DEFAULT_DATABASE_BASENAME = "storage"
CONFIG_PROFILES_DIR = "profiles"
DEFAULT_CONFIG = {
    "backend": "api",
    "backend_options": {
        "auto_create_first_user": None,
        "default_user": None,
        "default_conversation_id": None,
        "title_generation": {
            "provider": None,
            "model": None,
        },
    },
    "directories": {
        "cache": [
            "$DATA_DIR/cache",
        ],
        "templates": [
            "$CONFIG_DIR/profiles/$PROFILE/templates",
            "$CONFIG_DIR/templates",
        ],
        "presets": [
            "$CONFIG_DIR/presets",
            "$CONFIG_DIR/profiles/$PROFILE/presets",
        ],
        "plugins": [
            "$CONFIG_DIR/profiles/$PROFILE/plugins",
            "$CONFIG_DIR/plugins",
        ],
        "workflows": [
            "$CONFIG_DIR/workflows",
            "$CONFIG_DIR/profiles/$PROFILE/workflows",
        ],
        "tools": [
            "$CONFIG_DIR/tools",
            "$CONFIG_DIR/profiles/$PROFILE/tools",
        ],
    },
    "shell": {
        "prompt_prefix": "$TITLE$NEWLINE($TEMPERATURE/$MAX_SUBMISSION_TOKENS/$CURRENT_CONVERSATION_TOKENS): $SYSTEM_MESSAGE_ALIAS$NEWLINE$USER@$PRESET_OR_MODEL",
        "history_file": "%s%srepl_history.log" % (tempfile.gettempdir(), os.path.sep),
        "streaming": False,
    },
    "database": None,
    "model": {
        "default_preset": None,
        "default_system_message": "default",
        "system_message": {
            "programmer": SYSTEM_MESSAGE_PROGRAMMER,
            "creative_writer": SYSTEM_MESSAGE_CREATIVE_WRITER,
        },
    },
    "chat": {
        "log": {
            "enabled": False,
            "filepath": "lwe.log",
        },
    },
    "log": {
        "console": {
            "level": "error",
            "format": "%(name)s - %(levelname)s - %(message)s",
        },
    },
    "plugins": {
        "enabled": [
            "echo",
            "examples",
        ],
    },
    "debug": {
        "log": {
            "enabled": False,
            "filepath": "%s%slwe-debug.log" % (tempfile.gettempdir(), os.path.sep),
            "level": "debug",
            "format": "%(name)s - %(asctime)s - %(levelname)s - %(message)s",
        },
    },
}

# Shell specific constants.
COMMAND_LEADER = "/"
ACTIVE_ITEM_INDICATOR = "\U0001F7E2"  # Green circle.
DEFAULT_COMMAND = "ask"
DEFAULT_HISTORY_LIMIT = 20
SHELL_ONE_SHOT_COMMANDS = [
    "config",
]

# Interface-specific constants.
# These are the variables in this file that are available for substitution in
# help messages.
HELP_TOKEN_VARIABLE_SUBSTITUTIONS = [
    "COMMAND_LEADER",
    "DEFAULT_HISTORY_LIMIT",
    "SYSTEM_MESSAGE_DEFAULT",
    "OPEN_AI_MAX_TOKENS",
    "OPEN_AI_MIN_SUBMISSION_TOKENS",
    "OPEN_AI_DEFAULT_MAX_SUBMISSION_TOKENS",
]
