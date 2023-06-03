#!/usr/bin/python

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os

from ansible.module_utils.basic import AnsibleModule

from langchain.chat_models import ChatOpenAI
from langchain.schema import (
    HumanMessage,
    SystemMessage
)

DOCUMENTATION = r'''
---
module: lwe

short_description: Test retrieving a response from Langchain ChatOpenAI

version_added: "1.0.0"

description: Test retrieving a response from Langchain ChatOpenAI

options:
    prompt:
        description: The prompt to send to the model.
        required: true
        type: str
    model:
        description: The model name.
        required: false
        default: 'gpt-3.5-turbo'
        type: str
    temperature:
        description: The model temperature.
        required: false
        default: 0.7
        type: float

author:
    - Chad Phillips (@thehunmonkgroup)
'''

EXAMPLES = r'''
- name: Say hello
  lwe:
    prompt: "Say Hello!"
'''

RETURN = r'''
llm_response:
    description: The response from the model.
    type: dict
    returned: always
'''

def query_llm(prompt, model='gpt-3.5-turbo', temperature=0.7):
    llm = ChatOpenAI(temperature=temperature, model=model)
    messages = [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content=prompt),
    ]
    response = llm(messages)
    return response

def run_module():
    module_args = dict(
        prompt=dict(type='str', required=True),
        model=dict(type='str', required=False, default='gpt-3.5-turbo'),
        temperature=dict(type='float', required=False, default=0.7)
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

    prompt = module.params['prompt']
    model = module.params['model']
    temperature = module.params['temperature']

    try:
        response = query_llm(prompt, model, temperature)
        result['changed'] = True
        result['response'] = dict(response)
        result['content'] = response.content
    except ValueError as e:
        module.fail_json(msg=f"Error fetching LLM response: {e}", **result)

    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()
