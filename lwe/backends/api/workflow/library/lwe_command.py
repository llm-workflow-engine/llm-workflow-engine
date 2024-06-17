#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule

# from lwe.core import constants
from lwe.core.config import Config
from lwe.backends.api.repl import ApiRepl

DOCUMENTATION = r"""
---
module: lwe_command

short_description: Execute LWE REPL commands.

version_added: "1.0.0"

description: Execute LWE REPL commands.

options:
    command:
        description: The command to execute.
        required: true
        type: str
    arguments:
        description: The arguments to pass to the command.
        required: false
        default: ''
        type: str
    profile:
        description: The LWE profile to use.
        required: false
        default: 'default'
        type: str
    user:
        description: The LWE user to load for the execution, a user ID or username.
        required: false
        default: None (anonymous)
        type: int | str
    conversation_id:
        description: Set the current conversation to the specified ID.
        required: false
        default: None
        type: int

author:
    - Chad Phillips (@thehunmonkgroup)
"""

EXAMPLES = r"""
# Get the configured database path for the default profile.
- name: Get database path.
  lwe_command:
    command: config
    arguments: database

# Use User ID 1 in the 'test' profile,
# and output the chat history of the 1st conversation.
- name: Get chat history.
  lwe_command:
    command: chat
    arguments: 1
    profile: test
    user: 1
"""

RETURN = r"""
response:
    description: The response from the model.
    type: str
    returned: always
conversation_id:
    description: The conversation ID if the task run is associated with a conversation, or None otherwise.
    type: int
    returned: always
user_message:
    description: Human-readable user status message for the response.
    type: str
    returned: always
"""


def run_module():
    module_args = dict(
        command=dict(type="str", required=True),
        arguments=dict(type="str", required=False, default=""),
        profile=dict(type="str", required=False, default="default"),
        user=dict(type="raw", required=False),
        conversation_id=dict(type="int", required=False),
    )

    result = dict(changed=False, response=dict())

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    command = module.params["command"]
    arguments = module.params["arguments"]
    profile = module.params["profile"]
    user = module.params["user"]
    try:
        user = int(user)
    except Exception:
        pass
    conversation_id = module.params["conversation_id"]

    if module.check_mode:
        module.exit_json(**result)

    config = Config(profile=profile)
    config.load_from_file()
    config.set("debug.log.enabled", True)
    config.set("shell.streaming", False)
    config.set("backend_options.default_user", user)
    config.set("backend_options.default_conversation_id", conversation_id)
    repl = ApiRepl(config)
    repl.setup()

    repl.log.info("[lwe_command module]: Starting execution")

    _, repl_result = repl.run_command_get_response(command, arguments)
    try:
        success, response, user_message = repl_result
    except Exception:
        success = False
        user_message = repl_result

    if not success:
        result["failed"] = True
        repl.log.error(f"[lwe_command module]: Error executing LWE command: {user_message}")
        module.fail_json(msg=user_message, **result)

    result["changed"] = True
    result["response"] = response
    result["user_message"] = user_message
    repl.log.info("[lwe_command module]: execution completed successfully")
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
