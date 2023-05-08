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
