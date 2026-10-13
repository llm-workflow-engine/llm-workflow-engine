#!/usr/bin/python
"""Expose typed model decisions as a read-only Ansible workflow operation."""

from __future__ import annotations

from typing import cast

from ansible.module_utils.basic import AnsibleModule
from pydantic import ValidationError

from lwe.decisions import (
    DecisionError,
    DecisionRequest,
    DecisionService,
    DecisionSettings,
)

DOCUMENTATION = r"""
---
module: lwe_decide
short_description: Evaluate typed questions with a decision model.
description:
  - Returns probabilities and typed answers without creating chat conversations.
  - Install a plugin registering the selected decision provider before use.
options:
  state:
    description: String, JSON object, or JSON array to evaluate.
    type: raw
    required: true
  questions:
    description: Questions keyed by ID, with type, instructions, and criteria.
    type: dict
    required: true
  preset:
    description: Name under decisions.presets in the LWE profile configuration.
    type: str
  profile:
    description: LWE configuration profile.
    type: str
    default: default
  settings:
    description: Explicit decision settings, mutually exclusive with preset.
    type: dict
  images:
    description: Image HTTP(S) URLs, file URIs, data URLs, or raw base64, if supported by the provider.
    type: list
    elements: str
    default: []
  audio:
    description: Audio HTTP(S) URLs, file URIs, data URLs, or raw base64, if supported by the provider.
    type: list
    elements: str
    default: []
  videos:
    description: Video HTTP(S) URLs, file URIs, data URLs, or raw base64, if supported by the provider.
    type: list
    elements: str
    default: []
author:
  - LWE contributors
"""

EXAMPLES = r"""
- name: Classify a support request
  lwe_decide:
    preset: clef-triage
    state: "{{ support_request }}"
    questions:
      urgent:
        type: noul
        instructions: Does this request require urgent attention?
  register: triage

- name: Display urgent requests
  ansible.builtin.debug:
    msg: Urgent request
  when: triage.answers.urgent.noul >= 0.9
"""

RETURN = r"""
answers:
  description: Typed answers keyed by question ID; absent in check mode.
  type: dict
  returned: success outside check mode
model:
  description: Model reported by the provider.
  type: str
  returned: success outside check mode
provider:
  description: Selected decision provider.
  type: str
  returned: success outside check mode
usage:
  description: Usage reported by the provider.
  type: dict
  returned: success outside check mode
request_id:
  description: Provider request identifier when available.
  type: str
  returned: success outside check mode
elapsed_seconds:
  description: Total duration, including any retries.
  type: float
  returned: success outside check mode
"""


class DecisionModule:
    """Validate module inputs and delegate execution to the shared service."""

    def __init__(self, module: AnsibleModule) -> None:
        self.module = module

    def run(self) -> None:
        """Return dictionaries to Ansible and avoid model calls in check mode."""
        params = cast(dict[str, object], self.module.params)
        try:
            request = DecisionRequest.model_validate(
                {key: params[key] for key in ("state", "questions", "images", "audio", "videos")}
            )
            settings = (
                DecisionSettings.from_preset(
                    preset=cast(str, params["preset"]),
                    profile=cast(str, params["profile"]),
                )
                if params["preset"] is not None
                else DecisionSettings.model_validate(
                    {
                        key: value
                        for key, value in cast(dict[str, object], params["settings"]).items()
                        if value is not None
                    }
                )
            )
            service = DecisionService(settings)
            service.validate(request)
            if self.module.check_mode:
                self.module.exit_json(
                    changed=False,
                    skipped=True,
                    msg="Validated decision request; API call skipped in check mode",
                )
                return
            result = service.decide(request)
            self.module.exit_json(
                changed=False, **result.model_dump(mode="json", exclude_none=True)
            )
        except ValidationError as error:
            fields = ", ".join(".".join(str(item) for item in e["loc"]) for e in error.errors())
            self.module.fail_json(
                changed=False, msg=f"Invalid decision configuration/request: {fields}"
            )
        except (DecisionError, ValueError, OSError) as error:
            self.module.fail_json(changed=False, msg=str(error))


def main() -> None:
    """Create the Ansible entry point; Ansible owns argument parsing and logging."""
    module = AnsibleModule(
        argument_spec={
            "state": {"type": "raw", "required": True},
            "questions": {"type": "dict", "required": True},
            "preset": {"type": "str"},
            "profile": {"type": "str", "default": "default"},
            "settings": {
                "type": "dict",
                "options": {
                    "provider": {"type": "str", "required": True},
                    "model": {"type": "str", "required": True},
                    "options": {"type": "dict"},
                    "api_key": {"type": "str", "no_log": True},
                    "api_key_env_var": {"type": "str"},
                    "timeout": {"type": "float"},
                    "max_retries": {"type": "int"},
                },
            },
            "images": {
                "type": "list",
                "elements": "str",
                "default": [],
                "no_log": True,
            },
            "audio": {"type": "list", "elements": "str", "default": [], "no_log": True},
            "videos": {
                "type": "list",
                "elements": "str",
                "default": [],
                "no_log": True,
            },
        },
        required_one_of=[("preset", "settings")],
        mutually_exclusive=[("preset", "settings")],
        supports_check_mode=True,
    )
    DecisionModule(module).run()


if __name__ == "__main__":
    main()
