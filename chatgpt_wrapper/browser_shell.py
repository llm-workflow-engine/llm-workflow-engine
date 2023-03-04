from chatgpt_wrapper.gpt_shell import GPTShell

class BrowserShell(GPTShell):
    """
    A shell interpreter that serves as a front end to the ChatGPT class
    """

    def _conversation_from_messages(self, messages):
        message_parts = []
        for message in messages:
            if 'content' in message:
                message_parts.append("**%s**:" % message['author']['role'].capitalize())
                message_parts.extend(message['content']['parts'])
        content = "\n\n".join(message_parts)
        return content

    async def do_session(self, _):
        """
        Refresh session information

        This can resolve errors under certain scenarios.

        Examples:
            {leader}session
        """
        await self.chatgpt.refresh_session()
        usable = (
            "The session appears to be usable."
            if "accessToken" in self.chatgpt.session
            else "The session is not usable.  Try `install` mode."
        )
        self._print_markdown(f"* Session information refreshed.  {usable}")
