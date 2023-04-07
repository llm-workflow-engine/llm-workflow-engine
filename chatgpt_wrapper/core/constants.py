# Constants used across the modules are stored here.

import os
import tempfile

# Backend speciifc constants
RENDER_MODELS = {
    "default": "text-davinci-002-render-sha",
    "legacy-paid": "text-davinci-002-render-paid",
    "legacy-free": "text-davinci-002-render",
    "gpt4": "gpt-4"
}

OPENAPI_CHAT_RENDER_MODELS = {
    "default": "gpt-3.5-turbo",
    "turbo": "gpt-3.5-turbo",
    "turbo-0301": "gpt-3.5-turbo-0301",
    "gpt4": "gpt-4",
    "gpt4-0314": "gpt-4-0314",
    "gpt4-32k": "gpt-4-32k",
    "gpt4-32k-0314": "gpt-4-32k-0314",
}

SYSTEM_MESSAGE_DEFAULT = "You are a helpful assistant."
SYSTEM_MESSAGE_PROGRAMMER = "You are an expert programmer, who responds to questions with brief examples in code."
DEFAULT_TITLE_GENERATION_SYSTEM_PROMPT = 'You write short 3-5 word titles for any content'
DEFAULT_TITLE_GENERATION_USER_PROMPT = 'Write a title for this content:'

OPENAPI_MAX_TOKENS = 4096
OPENAPI_MIN_SUBMISSION_TOKENS = 1
OPENAPI_DEFAULT_MAX_SUBMISSION_TOKENS = 4000

OPENAPI_DEFAULT_TEMPERATURE = 0.9
OPENAPI_TEMPERATURE_MIN = 0
OPENAPI_TEMPERATURE_MAX = 2

OPENAPI_DEFAULT_TOP_P = 1
OPENAPI_TOP_P_MIN = 0
OPENAPI_TOP_P_MAX = 1

OPENAPI_DEFAULT_PRESENCE_PENALTY = 0.6
OPENAPI_PRESENCE_PENALTY_MIN = -2
OPENAPI_PRESENCE_PENALTY_MAX = 2

OPENAPI_DEFAULT_FREQUENCY_PENALTY = 0
OPENAPI_FREQUENCY_PENALTY_MIN = -2
OPENAPI_FREQUENCY_PENALTY_MAX = 2

# Config specific constants.
DEFAULT_PROFILE = 'default'
DEFAULT_CONFIG_DIR = 'chatgpt-wrapper'
DEFAULT_DATABASE_BASENAME = 'storage'
CONFIG_PROFILES_DIR = 'profiles'
DEFAULT_CONFIG = {
    'backend': 'chatgpt-api',
    'shell': {
        'prompt_prefix': '($TEMPERATURE/$TOP_P/$PRESENCE_PENALTY/$FREQUENCY_PENALTY/$MAX_SUBMISSION_TOKENS/$CURRENT_CONVERSATION_TOKENS)$NEWLINE$USER@$MODEL',
        'history_file': '%s%srepl_history.log' % (tempfile.gettempdir(), os.path.sep),
    },
    'database': None,
    'browser': {
        'provider': 'firefox',
        'debug': False,
    },
    'chat': {
        'model': 'default',
        'model_customizations': {
            'temperature': OPENAPI_DEFAULT_TEMPERATURE,
            'top_p': OPENAPI_DEFAULT_TOP_P,
            'presence_penalty': OPENAPI_DEFAULT_PRESENCE_PENALTY,
            'frequency_penalty': OPENAPI_DEFAULT_FREQUENCY_PENALTY,
            'max_submission_tokens': OPENAPI_DEFAULT_MAX_SUBMISSION_TOKENS,
            'system_message': {
                'programmer': SYSTEM_MESSAGE_PROGRAMMER,
            },
        },
        'streaming': False,
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
    'OPENAPI_DEFAULT_TEMPERATURE',
    'OPENAPI_TEMPERATURE_MIN',
    'OPENAPI_TEMPERATURE_MAX',
    'OPENAPI_DEFAULT_TOP_P',
    'OPENAPI_TOP_P_MIN',
    'OPENAPI_TOP_P_MAX',
    'OPENAPI_DEFAULT_PRESENCE_PENALTY',
    'OPENAPI_PRESENCE_PENALTY_MIN',
    'OPENAPI_PRESENCE_PENALTY_MAX',
    'OPENAPI_DEFAULT_FREQUENCY_PENALTY',
    'OPENAPI_FREQUENCY_PENALTY_MIN',
    'OPENAPI_FREQUENCY_PENALTY_MAX',
]
