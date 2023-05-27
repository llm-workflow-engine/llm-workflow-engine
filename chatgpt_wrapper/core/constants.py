# Constants used across the modules are stored here.

import os
import tempfile

PROVIDER_PREFIX = 'provider_'

# Backend speciifc constants
API_BACKEND_DEFAULT_MODEL = "gpt-3.5-turbo"

SYSTEM_MESSAGE_DEFAULT = "You are a helpful assistant."
SYSTEM_MESSAGE_PROGRAMMER = "You are an expert programmer, who responds to questions with brief examples in code."
DEFAULT_TITLE_GENERATION_SYSTEM_PROMPT = 'You write short 3-5 word titles for any content'
DEFAULT_TITLE_GENERATION_USER_PROMPT = 'Write a title for this content:'

OPENAPI_MAX_TOKENS = 4096
OPENAPI_MIN_SUBMISSION_TOKENS = 1
OPENAPI_DEFAULT_MAX_SUBMISSION_TOKENS = 4000

# Config specific constants.
DEFAULT_PROFILE = 'default'
DEFAULT_CONFIG_DIR = 'chatgpt-wrapper'
DEFAULT_DATABASE_BASENAME = 'storage'
CONFIG_PROFILES_DIR = 'profiles'
DEFAULT_CONFIG = {
    'backend': 'api',
    'shell': {
        'prompt_prefix': '($TEMPERATURE/$MAX_SUBMISSION_TOKENS/$CURRENT_CONVERSATION_TOKENS): $SYSTEM_MESSAGE_ALIAS$NEWLINE$USER@$PRESET_OR_MODEL',
        'history_file': '%s%srepl_history.log' % (tempfile.gettempdir(), os.path.sep),
    },
    'database': None,
    'browser': {
        'provider': 'firefox',
        'debug': False,
        'plugins': [],
    },
    'model': {
        'default_preset': None,
        'default_system_message': 'default',
        'streaming': False,
        'system_message': {
            'programmer': SYSTEM_MESSAGE_PROGRAMMER,
        },
    },
    'chat': {
        'log': {
            'enabled': False,
            'filepath': 'chatgpt.log',
        },
    },
    'log': {
        'console': {
            'level': 'error',
            'format': '%(name)s - %(levelname)s - %(message)s',
        },
    },
    'plugins': {
        'enabled': [
            'echo',
        ],
    },
    'debug': {
        'log': {
            'enabled': False,
            'filepath': '%s%schatgpt-debug.log' % (tempfile.gettempdir(), os.path.sep),
            'level': 'debug',
            'format': '%(name)s - %(asctime)s - %(levelname)s - %(message)s',
        },
    },
}

# Shell specific constants.
COMMAND_LEADER = '/'
LEGACY_COMMAND_LEADER = '!'
DEFAULT_COMMAND = 'ask'
DEFAULT_HISTORY_LIMIT = 20
SHELL_ONE_SHOT_COMMANDS = [
    'install',
    'reinstall',
    'config',
]

# Interface-specific constants.
NO_TITLE_TEXT = "No title"
# These are the variables in this file that are available for substitution in
# help messages.
HELP_TOKEN_VARIABLE_SUBSTITUTIONS = [
    'COMMAND_LEADER',
    'DEFAULT_HISTORY_LIMIT',
    'SYSTEM_MESSAGE_DEFAULT',
    'OPENAPI_MAX_TOKENS',
    'OPENAPI_MIN_SUBMISSION_TOKENS',
    'OPENAPI_DEFAULT_MAX_SUBMISSION_TOKENS',
]
