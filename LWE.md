LLM Workflow Engine (LWE) is a command-line tool and Python module that streamlines common LLM-related tasks, such as managing reusable prompts, stress-testing prompts across different LLM configurations, and designing multi-step workflows that involve LLMs.

At its heart, LWE has four main components:

1. **Conversation management:**
   * Start new conversations
   * Review/extend/remove old conversations
2. **Model configuration:**
   * Configure LLMs across different providers
   * Customize model attributes (temperature, etc.)
   * Save/reload existing configurations
3. **Prompt templates:**
   * Design/save new prompts
   * Include/pass variables to prompts during execution
   * Connect a specific prompt to a specific model configuration
4. **Workflows:**
   * Design multi-step workflows using YAML
   * Integrate prompt templates
   * Integrate model configurations
   * Save LLM interactions to conversations

When combined, these four components provide a lot of flexibility and power for working with LLMs.

Other LWE nicities:

1. **Plugins:**
   * Command plugins: Write a command for LWE that accomplishes some new task
   * Provider plugins: Easily add new LLM providers into the LWE ecosystem
2. **Custom system messages:** Easily create and use different system messages for supported providers
3. **Command completion:** Tab completion for most commands and arguments
4. **Managed database updates:** Automatic database upgrades for new releases
5. **Examples**: To help jump start your productivity
   * Prompt templates
   * Workflows
6. **Ansible-compatible playbooks**: Re-use LWE workflows inside a larger [Ansible](https://docs.ansible.com) ecosystem
7. **Automatic conversation titles**: ChatGPT generates short titles for your conversations
8. **Token tracking**: For supported providers, see the number of tokens you've consumed, and auto-prune messages from long conversations
9. **Customizable user prompt**
10. **Multi-user management**
11. **Streaming responses:** For supported providers
12. **Command line help**
13. **System clipboard integration**
14. **Edit prompts in your system editor (Vim, etc.)**
