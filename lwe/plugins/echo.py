from lwe.core.plugin import Plugin
import lwe.core.util as util


class Echo(Plugin):
    """
    Simple echo plugin, echos back the text you give it
    """

    def default_config(self):
        """
        The default configuration for this plugin.
        This is called by the plugin manager after the plugin is initialized.
        The user can override these settings in their profile configuration,
        under the key 'plugins.echo'.
        """
        return {
            "response": {
                "prefix": "Echo",
            },
        }

    def setup(self):
        """
        Setup the plugin. This is called by the plugin manager after the backend
        is initialized.
        """
        self.log.info(f"This is the echo plugin, running with backend: {self.backend.name}")
        # Accessing the final configuration of the plugin.
        self.response_prefix = self.config.get("plugins.echo.response.prefix")

    def get_shell_completions(self, _base_shell_completions):
        """Example of provided shell completions."""
        commands = {}
        commands[util.command_with_leader("echo")] = util.list_to_completion_hash(
            ["one", "two", "three"]
        )
        return commands

    def command_echo(self, arg):
        """
        Echo command, a simple plugin example

        This command is provided as an example of extending functionality via a plugin.

        Arguments:
            text: The text to echo

        Examples:
            {COMMAND} one
        """
        if not arg:
            return False, arg, "Argument is required"
        return True, arg, f"{self.response_prefix}: {arg}"
