from chatgpt_wrapper.core.plugin import Plugin
import chatgpt_wrapper.core.util as util

class Test(Plugin):

    def default_config(self):
        """
           The default configuration for this plugin.
           This is called by the plugin manager after the plugin is initialized.
           The user can override these settings in their profile configuration,
           under the key 'plugins.test'.
        """
        return {
            'response': {
                'prefix': 'Test',
            },
        }

    def setup(self):
        """
        Setup the plugin. This is called by the plugin manager after the backend
        is initialized.
        """
        self.log.info(f"This is the test plugin, running with backend: {self.backend.name}")
        # Accessing the final configuration of the plugin.
        self.response_prefix = self.config.get('plugins.test.response.prefix')

    def get_shell_completions(self, _base_shell_completions):
        """Example of provided shell completions."""
        commands = {}
        commands[util.command_with_leader('test')] = util.list_to_completion_hash(['one', 'two', 'three'])
        return commands

    def do_test(self, arg):
        """
        Test plugin command

        Examples:
            {COMMAND} one
        """
        if not arg:
            return False, arg, "Argument is required"
        return True, arg, f"{self.response_prefix}: {arg}"
