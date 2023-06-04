#!/usr/bin/python

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule

from chatgpt_wrapper.core.config import Config
from chatgpt_wrapper import ApiBackend

DOCUMENTATION = r'''
---
module: lwe

short_description: Make LLM requests via LWE.

version_added: "1.0.0"

description: Make LLM requests via LWE.

options:
    message:
        description: The message to send to the model.
        required: true
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
    user:
        description: The LWE user to load for the execution
        required: false
        default: None (anonymous)
        type: str
    conversation_id:
        description: An existing LWE conversation to use.
        required: false
        default: None (anonymous, or new conversation if user is provided)
        type: int

author:
    - Chad Phillips (@thehunmonkgroup)
'''

EXAMPLES = r'''
- name: Say hello
  lwe:
    message: "Say Hello!"
'''

# TODO: Clarify this.
RETURN = r'''
llm_response:
    description: The response from the model.
    type: dict
    returned: always
'''

def run_module():
    module_args = dict(
        message=dict(type='str', required=True),
        profile=dict(type='str', required=False, default='default'),
        # provider=dict(type='str', required=False, default='chat_openai'),
        # model=dict(type='str', required=False, default='gpt-3.5-turbo'),
        preset=dict(type='str', required=False, default=None),
        user=dict(type='str', required=False, default=None),
        conversation_id=dict(type='int', required=False, default=None),
    )

    result = dict(
        changed=False,
        response=dict()
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    if module.check_mode:
        module.exit_json(**result)

    message = module.params['message']
    profile = module.params['profile']
    # provider = module.params['provider']
    # model = module.params['model']
    preset = module.params['preset']
    user = module.params['user']
    conversation_id = module.params['conversation_id']

    config = Config(profile=profile)
    config.set('debug.log.enabled', True)
    config.set('model.default_preset', preset)
    config.set('backend_options.default_user', user)
    config.set('backend_options.default_conversation_id', conversation_id)
    gpt = ApiBackend(config)
    success, response, user_message = gpt.ask(message)
    if success:
        result['changed'] = True
        result['response'] = response
        result['conversation_id'] = gpt.conversation_id
        result['user_message'] = user_message
    else:
        module.fail_json(msg=f"Error fetching LLM response: {user_message}", **result)

    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()
