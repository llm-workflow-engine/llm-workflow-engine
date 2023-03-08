from chatgpt_wrapper.chatgpt import AsyncChatGPT
from chatgpt_wrapper.gpt_shell import GPTShell

class BrowserShell(GPTShell):
    """
    A shell interpreter that serves as a front end to the ChatGPT class
    """

    def configure_commands(self):
        super().configure_commands()
        self.commands.extend([method[3:] for method in dir(__class__) if callable(getattr(__class__, method)) and method.startswith("do_")])

    async def configure_backend(self):
        self.backend = await AsyncChatGPT(self.config).create(timeout=90)

    async def do_session(self, _):
        """
        Refresh session information

        This can resolve errors under certain scenarios.

        Examples:
            {COMMAND_LEADER}session
        """
        await self.backend.refresh_session()
        usable = (
            "The session appears to be usable."
            if "accessToken" in self.backend.session
            else "The session is not usable.  Try `install` mode."
        )
        self._print_markdown(f"* Session information refreshed.  {usable}")

    async def cleanup(self):
        await self.backend.cleanup()
