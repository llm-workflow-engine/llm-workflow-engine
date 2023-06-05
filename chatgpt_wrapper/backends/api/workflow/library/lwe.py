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

author:
    - Chad Phillips (@thehunmonkgroup)
'''

EXAMPLES = r'''
# Simple message with default values
- name: Say hello
  lwe:
    message: "Say Hello!"

# Start a new conversation with this response
- name: Start conversation
  lwe:
    message: "What are the three primary colors?"
    # User ID or username
    user: 1
    register: result

# Continue a conversation with this response
- name: Continue conversation
  lwe:
    message: "Provide more detail about your previous response"
    user: 1
    conversation_id: result.conversation_id

# Use the 'mytemplate.md' template, passing in a few template variables
- name: Templated prompt
  lwe:
    template: mytemplate.md
    template_vars:
        foo: bar
        baz: bang

# Use the 'test' profile, and a pre-configured provider/model preset 'mypreset'
- name: Continue conversation
  lwe:
    message: "Say three things about bacon"
    profile: test
    preset: mypreset

'''

RETURN = r'''
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
'''

def run_module():
    module_args = dict(
        message=dict(type='str', required=False),
        profile=dict(type='str', required=False, default='default'),
        # provider=dict(type='str', required=False, default='chat_openai'),
        # model=dict(type='str', required=False, default='gpt-3.5-turbo'),
        preset=dict(type='str', required=False),
        template=dict(type='str', required=False),
        template_vars=dict(type='dict', required=False),
        user=dict(type='raw', required=False),
        conversation_id=dict(type='int', required=False),
    )

    result = dict(
        changed=False,
        response=dict()
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    message = module.params['message']
    profile = module.params['profile']
    # provider = module.params['provider']
    # model = module.params['model']
    preset = module.params['preset']
    template_name = module.params['template']
    template_vars = module.params['template_vars'] or {}
    user = module.params['user']
    try:
        user = int(user)
    except Exception:
        pass
    conversation_id = module.params['conversation_id']

    if (message is None and template_name is None) or (message is not None and template_name is not None):
        module.fail_json(msg="One and only one of 'message' or 'template' arguments must be set.")

    if module.check_mode:
        module.exit_json(**result)

    config = Config(profile=profile)
    config.set('debug.log.enabled', True)
    config.set('model.default_preset', preset)
    config.set('backend_options.default_user', user)
    config.set('backend_options.default_conversation_id', conversation_id)
    gpt = ApiBackend(config)

    gpt.log.info("[lwe module]: Starting execution")

    if template_name is not None:
        gpt.log.debug(f"[lwe module]: Using template: {template_name}")
        success, template_name, user_message = gpt.template_manager.ensure_template(template_name)
        if not success:
            gpt.log.error(f"[lwe module]: {user_message}")
            module.fail_json(msg=user_message, **result)
        _, variables = gpt.template_manager.get_template_and_variables(template_name)
        substitutions = gpt.template_manager.process_template_builtin_variables(template_name, variables)
        substitutions.update(template_vars)
        message, overrides = gpt.template_manager.build_message_from_template(template_name, substitutions)
        if 'request_overrides' in overrides and 'preset' in overrides['request_overrides']:
            preset_name = overrides['request_overrides'].pop('preset')
            success, llm, user_message = gpt.set_override_llm(preset_name)
            if success:
                gpt.log.info(f"[lwe module]: Switching to preset '{preset_name}' for template: {template_name}")
            else:
                gpt.log.error(f"[lwe module]: {user_message}")
                module.fail_json(msg=user_message, **result)
        gpt.log.info(f"[lwe module]: Running template: {template_name}")

    success, response, user_message = gpt.ask(message)
    gpt.set_override_llm()

    if not success or not response:
        result['failed'] = True
        message = user_message
        if not success:
            message = f"Error fetching LLM response: {user_message}"
        elif not response:
            message = f"Empty LLM response: {user_message}"
        gpt.log.error(f"[lwe module]: {message}")
        module.fail_json(msg=message, **result)

    result['changed'] = True
    result['response'] = response
    result['conversation_id'] = gpt.conversation_id
    result['user_message'] = user_message
    gpt.log.info("[lwe module]: execution completed successfully")
    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()
