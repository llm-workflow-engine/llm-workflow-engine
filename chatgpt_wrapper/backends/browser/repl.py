import chatgpt_wrapper.core.util as util
from chatgpt_wrapper.backends.browser.backend import BrowserBackend
from chatgpt_wrapper.core.repl import Repl

class BrowserRepl(Repl):
    """
    A shell interpreter that serves as a front end to the BrowserBackend class
    """

    def configure_shell_commands(self):
        self.commands = util.introspect_commands(__class__)

    def get_custom_shell_completions(self):
        self.base_shell_completions[util.command_with_leader('model')] = self.backend.provider.customizations_to_completions()
        return {}

    def configure_backend(self):
        self.backend = BrowserBackend(self.config)

    def launch_backend(self, interactive=True):
        self.backend.launch_browser()

    def build_shell_user_prefix(self):
        return f"{self.backend.model} "

    def do_session(self, _):
        """
        Refresh session information

        This can resolve errors under certain scenarios.

        Examples:
            {COMMAND}
        """
        self.backend.refresh_session()
        usable = (
            "The session appears to be usable."
            if "accessToken" in self.backend.session
            else "The session is not usable.  Try `install` mode."
        )
        util.print_markdown(f"* Session information refreshed.  {usable}")

    def get_plugin_list(self):
        success, plugins, user_message = self.backend.get_plugins()
        if not success:
            return success, plugins, user_message
        plugin_list = {p['id']: {
            'domain': p['domain'],
            'namespace': p['namespace'],
            'name': p['manifest']['name_for_human'],
            'description': p['manifest']['description_for_human'],
        } for p in plugins}
        return True, plugin_list, "Processed plugin list"

    def do_plugins(self, arg):
        """
        Retrieve information on available plugins

        Plugins are retrieved from OpenAI's official approved plugins list.

        NOTE: Not all users may have access to all plugins.

        Arguments:
            filter_string: Optional. String to filter plugins by. Domain, name, and description are matched.

        Examples:
            {COMMAND}
            {COMMAND} youtube
        """
        success, plugins, user_message = self.get_plugin_list()
        if not success:
            return success, plugins, user_message
        plugin_list = []
        for id, data in plugins.items():
            content = f"##### Provider: {data['domain']}, {data['namespace']}\n* **ID: {id}**"
            if 'description' in data:
                content += f"\n* Description: *{data['description']}*"
            if not arg or arg.lower() in content.lower():
                plugin_list.append(content)
        util.print_markdown("## Plugins:\n\n%s" % "\n".join(plugin_list))
