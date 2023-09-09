# Derived from the Ansible core pause action plugin.
#
# Copyright 2012, Tim Bielawa <tbielawa@redhat.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import absolute_import, division, print_function

__metaclass__ = type

import datetime
import time

from ansible.errors import AnsibleError, AnsiblePromptInterrupt, AnsiblePromptNoninteractive
from ansible.module_utils.common.text.converters import to_text
from ansible.plugins.action import ActionBase
from ansible.utils.display import Display

from lwe.core.editor import pipe_editor

DOCUMENTATION = """
  module: lwe_input
  short_description: Pauses execution until input is received
  description:
    - This module pauses the execution of a playbook until the user provides input.
    - The user can provide input through the command line or by opening an editor.
  options:
    echo:
      description:
        - If set to True, the user's input will be displayed on the screen.
        - If set to False, the user's input will be hidden.
      type: bool
      default: True
    prompt:
      description:
        - The custom prompt message to display before waiting for user input.
      type: str
  author:
    - Chad Phillips (@thehunmonkgroup)
"""

EXAMPLES = """
  - name: Pause execution and wait for user input
    lwe_input:

  - name: Pause execution and wait for user input with custom prompt
    lwe_input:
      prompt: "Please enter your name"

  - name: Pause execution and wait for user input with hidden output
    lwe_input:
      echo: False
"""

RETURN = """
  stdout:
    description: Standard output of the task, showing the duration of the pause.
    type: str
    returned: always
  stop:
    description: The end time of the pause.
    type: str
    returned: always
  delta:
    description: The duration of the pause in seconds.
    type: int
    returned: always
  user_input:
    description: The input provided by the user.
    type: str
    returned: always
"""

display = Display()


class ActionModule(ActionBase):
    """pauses execution until input is received"""

    BYPASS_HOST_LOOP = True

    def run(self, tmp=None, task_vars=None):
        """run the lwe_input action module"""
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp  # tmp no longer has any effect

        validation_result, new_module_args = self.validate_argument_spec(
            argument_spec={
                "echo": {"type": "bool", "default": True},
                "prompt": {"type": "str"},
            },
        )

        prompt = None
        echo = new_module_args["echo"]
        echo_prompt = ""
        result.update(
            dict(
                changed=False,
                rc=0,
                stderr="",
                stdout="",
                start=None,
                stop=None,
                delta=None,
                echo=echo,
            )
        )

        editor_blurb = "Enter 'e' to open an editor"

        # Add a note saying the output is hidden if echo is disabled
        if not echo:
            echo_prompt = " (output is hidden)"

        if new_module_args["prompt"]:
            prompt = "\n[%s]\n%s\n\n%s%s:" % (
                self._task.get_name().strip(),
                editor_blurb,
                new_module_args["prompt"],
                echo_prompt,
            )
        else:
            # If no custom prompt is specified, set a default prompt
            prompt = "\n[%s]\n%s\n\n%s%s:" % (
                self._task.get_name().strip(),
                editor_blurb,
                "Press enter to continue, Ctrl+C to interrupt",
                echo_prompt,
            )

        ########################################################################
        # Begin the hard work!

        start = time.time()
        result["start"] = to_text(datetime.datetime.now())
        result["user_input"] = b""

        default_input_complete = None

        user_input = b""
        try:
            _user_input = display.prompt_until(
                prompt, private=not echo, complete_input=default_input_complete
            )
        except AnsiblePromptInterrupt:
            user_input = None
        except AnsiblePromptNoninteractive:
            display.warning("Not waiting for response to prompt as stdin is not interactive")
        else:
            user_input = _user_input
        # user interrupt
        if user_input is None:
            prompt = "Press 'C' to continue the play or 'A' to abort \r"
            try:
                user_input = display.prompt_until(
                    prompt, private=not echo, interrupt_input=(b"a",), complete_input=(b"c",)
                )
            except AnsiblePromptInterrupt as err:
                raise AnsibleError("user requested abort!") from err
        elif user_input.strip() == b"e":
            display.display("Editor requested")
            user_input = pipe_editor("", suffix="md")

        duration = time.time() - start
        result["stop"] = to_text(datetime.datetime.now())
        result["delta"] = int(duration)
        duration = round(duration, 2)
        result["stdout"] = "Paused for %s seconds" % duration
        result["user_input"] = to_text(user_input, errors="surrogate_or_strict")
        return result
