#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os

from ansible.module_utils.basic import AnsibleModule

# from lwe.core import constants
from lwe.core.config import Config
from lwe import ApiBackend
import lwe.core.util as util

DOCUMENTATION = r"""
---
module: lwe_llm

short_description: Make LLM requests via LWE.

version_added: "1.0.0"

description: Make LLM requests via LWE.

options:
    message:
        description: The message to send to the model.
        required: true if template not provided
        type: str
    profile:
        description: The LWE profile to use.
        required: false
        default: 'default'
        type: str
    preset:
        description: The LWE preset to use.
        required: false
        default: None
        type: str
    preset_overrides:
        description: A dictionary of metadata and model customization overrides to apply to the preset when running the template.
        required: false
        default: None
        type: dict
    system_message:
        description: The LWE system message to use, either an alias or custom message.
        required: false
        default: None
        type: str
    max_submission_tokens:
        description: The maximum number of tokens that can be submitted. Default is max for the model.
        required: false
        default: None
        type: int
    template:
        description: An LWE template to use for constructing the prompt.
        required: true if message not provided
        default: None
        type: str
    template_vars:
        description: A dictionary of variables to substitute into the template.
        required: false
        default: None
        type: dict
    user:
        description: The LWE user to load for the execution, a user ID or username.
                     NOTE: A user must be provided to start or continue a conversation.
        required: false
        default: None (anonymous)
        type: str
    conversation_id:
        description: An existing LWE conversation to use.
                     NOTE: A conversation_id must be provided to continue a conversation.
        required: false
        default: None (anonymous, or new conversation if user is provided)
        type: int
    title:
        description: Custom title for the conversation.
                     NOTE: This is only used if a user_id is provided for a new conversation.
        required: false
        default: None
        type: str

author:
    - Chad Phillips (@thehunmonkgroup)
"""

EXAMPLES = r"""
# Simple message with default values
- name: Say hello
  lwe_llm:
    message: "Say Hello!"

# Start a new conversation with this response
- name: Start conversation
  lwe_llm:
    message: "What are the three primary colors?"
    max_submission_tokens: 512
    # User ID or username
    user: 1
    register: result

# Continue a conversation with this response
- name: Continue conversation
  lwe_llm:
    message: "Provide more detail about your previous response"
    user: 1
    conversation_id: result.conversation_id

# Use the 'mytemplate.md' template, passing in a few template variables
- name: Templated prompt
  lwe_llm:
    template: mytemplate.md
    template_vars:
        foo: bar
        baz: bang

# Use the 'test' profile, a pre-configured provider/model preset 'mypreset',
# and override some of the preset configuration.
- name: Continue conversation
  lwe_llm:
    message: "Say three things about bacon"
    system_message: "You are a bacon connoisseur"
    profile: test
    preset: mypreset
    preset_overrides:
        metadata:
            return_on_tool_call: true
        model_customizations:
            temperature: 1

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
        message=dict(type="str", required=False),
        profile=dict(type="str", required=False, default="default"),
        # provider=dict(type='str', required=False, default='chat_openai'),
        # model=dict(type='str', required=False, default=constants.API_BACKEND_DEFAULT_MODEL),
        preset=dict(type="str", required=False),
        preset_overrides=dict(type="dict", required=False),
        system_message=dict(type="str", required=False),
        max_submission_tokens=dict(type="int", required=False),
        template=dict(type="str", required=False),
        template_vars=dict(type="dict", required=False),
        user=dict(type="raw", required=False),
        conversation_id=dict(type="int", required=False),
        title=dict(type="str", required=False),
    )

    result = dict(changed=False, response=dict())

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    message = module.params["message"]
    profile = module.params["profile"]
    # provider = module.params['provider']
    # model = module.params['model']
    preset = module.params["preset"]
    preset_overrides = module.params["preset_overrides"]
    system_message = module.params["system_message"]
    max_submission_tokens = module.params["max_submission_tokens"]
    template_name = module.params["template"]
    template_vars = module.params["template_vars"] or {}
    user = module.params["user"]
    try:
        user = int(user)
    except Exception:
        pass
    conversation_id = module.params["conversation_id"]
    title = module.params["title"]

    if (message is None and template_name is None) or (
        message is not None and template_name is not None
    ):
        module.fail_json(msg="One and only one of 'message' or 'template' arguments must be set.")

    if module.check_mode:
        module.exit_json(**result)

    config_args = {
        "profile": profile,
    }
    config_dir = os.environ.get("LWE_CONFIG_DIR", None)
    data_dir = os.environ.get("LWE_DATA_DIR", None)
    if config_dir:
        config_args["config_dir"] = config_dir
    if data_dir:
        config_args["data_dir"] = data_dir
    config = Config(**config_args)
    config.load_from_file()
    config.set("debug.log.enabled", True)
    config.set("model.default_preset", preset)
    config.set("backend_options.default_user", user)
    config.set("backend_options.default_conversation_id", conversation_id)
    gpt = ApiBackend(config)
    if max_submission_tokens:
        gpt.set_max_submission_tokens(max_submission_tokens)
    gpt.set_return_only(True)

    gpt.log.info("[lwe_llm module]: Starting execution")

    overrides = {
        "request_overrides": {},
    }
    if preset_overrides:
        overrides["request_overrides"]["preset_overrides"] = preset_overrides
    if system_message:
        overrides["request_overrides"]["system_message"] = system_message
    if title:
        overrides["request_overrides"]["title"] = title
    if template_name is not None:
        gpt.log.debug(f"[lwe_llm module]: Using template: {template_name}")
        success, response, user_message = gpt.template_manager.get_template_variables_substitutions(
            template_name
        )
        if not success:
            gpt.log.error(f"[lwe_llm module]: {user_message}")
            module.fail_json(msg=user_message, **result)
        _template, _variables, substitutions = response
        util.merge_dicts(substitutions, template_vars)
        success, response, user_message = gpt.run_template_setup(template_name, substitutions)
        if not success:
            gpt.log.error(f"[lwe_llm module]: {user_message}")
            module.fail_json(msg=user_message, **result)
        message, template_overrides = response
        util.merge_dicts(template_overrides, overrides)
        gpt.log.info(f"[lwe_llm module]: Running template: {template_name}")
        success, response, user_message = gpt.run_template_compiled(message, template_overrides)
        if not success:
            gpt.log.error(f"[lwe_llm module]: {user_message}")
            module.fail_json(msg=user_message, **result)
    else:
        success, response, user_message = gpt.ask(message, **overrides)

    if not success or not response:
        result["failed"] = True
        message = user_message
        if not success:
            message = f"Error fetching LLM response: {user_message}"
        elif not response:
            message = f"Empty LLM response: {user_message}"
        gpt.log.error(f"[lwe_llm module]: {message}")
        module.fail_json(msg=message, **result)

    result["changed"] = True
    result["response"] = response
    result["conversation_id"] = gpt.conversation_id
    result["user_message"] = user_message
    gpt.log.info("[lwe_llm module]: execution completed successfully")
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
