from langchain.agents import initialize_agent
from langchain.agents.agent_toolkits import ZapierToolkit
from langchain.utilities.zapier import ZapierNLAWrapper

from chatgpt_wrapper.core.plugin import Plugin

class Zap(Plugin):

    def incompatible_backends(self):
        return [
            'chatgpt-browser',
        ]

    def default_config(self):
        return {
            'agent': {
                'verbose': True,
            },
        }

    def setup(self):
        self.log.info(f"Setting up zap plugin, running with backend: {self.backend.name}")
        self.zapier = ZapierNLAWrapper()
        self.toolkit = ZapierToolkit.from_zapier_nla_wrapper(self.zapier)
        self.agent_verbose = self.config.get('plugins.zap.agent.verbose')

    def do_zap(self, arg):
        """
        Send natural language commands to Zapier actions

        Requires exporting a Zapier Personal API Key into the following environment variable:
            ZAPIER_NLA_API_KEY

        To learn more: https://nla.zapier.com/get-started/

        Arguments:
            command: The natural language command to send to Zapier.

        Examples:
            {COMMAND} send an email to foo@bar.com with a random top 10 list
        """
        if not arg:
            return False, arg, "Command is required"
        try:
            agent = initialize_agent(self.toolkit.get_tools(), self.make_llm(), agent="zero-shot-react-description", verbose=self.agent_verbose)
            result = agent.run(arg)
        except ValueError as e:
            return False, arg, e
        return True, arg, result
