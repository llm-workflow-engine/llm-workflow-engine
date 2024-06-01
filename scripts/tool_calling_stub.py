#!/usr/bin/env python

import argparse
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from lwe import debug

# Import model providers
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_vertexai import ChatVertexAI
from langchain_cohere import ChatCohere
from langchain_fireworks import ChatFireworks
from langchain_mistralai import ChatMistralAI

TOOL_CHOICE_NOT_IMPLEMENTED_PROVIDERS = [
    "vertexai",
    "cohere",
]


@tool
def add(a: int, b: int) -> int:
    """Adds a and b."""
    return a + b


@tool
def multiply(a: int, b: int) -> int:
    """Multiplies a and b."""
    return a * b


def get_model_provider(provider: str):
    if provider == "openai":
        return ChatOpenAI(model="gpt-4o")
    elif provider == "anthropic":
        return ChatAnthropic(model="claude-3-sonnet-20240229")
    elif provider == "vertexai":
        return ChatVertexAI(model="gemini-pro")
    elif provider == "cohere":
        return ChatCohere(model="command-r")
    elif provider == "fireworks":
        return ChatFireworks(model="accounts/fireworks/models/firefunction-v1", temperature=0)
    elif provider == "mistralai":
        return ChatMistralAI(model="mistral-large-latest")
    else:
        raise ValueError(f"Unknown provider: {provider}")


def main():
    parser = argparse.ArgumentParser(description="Test tool calling.")
    parser.add_argument(
        "--provider",
        type=str,
        choices=["openai", "anthropic", "vertexai", "cohere", "fireworks", "mistralai"],
        required=True,
        help="The model provider to use.",
    )
    args = parser.parse_args()
    llm = get_model_provider(args.provider)

    # Define messages and tools
    messages = [
        SystemMessage(
            content="You are a helpful assistant, who responds with the most brief answer to the question."
        ),
        HumanMessage(content="What is 3 * 12? Use the provided 'multiply' tool"),
    ]
    tools = [add, multiply]

    kwargs = {}
    if args.provider not in TOOL_CHOICE_NOT_IMPLEMENTED_PROVIDERS:
        kwargs["tool_choice"] = "any"
    llm_with_tools = llm.bind_tools(tools, **kwargs)
    ai_response = llm_with_tools.invoke(messages)
    messages.append(ai_response)
    debug.console(ai_response)


if __name__ == "__main__":
    main()
