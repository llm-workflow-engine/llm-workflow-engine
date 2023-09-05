#!/usr/bin/env python

from lwe import ApiBackend
from lwe.core import constants


def test_api_backend_get_history(test_config):
    # test_config.set('debug.log.enabled', True)
    test_config.set('backend_options.default_user', 1)
    gpt = ApiBackend(test_config)
    for i in range(3):
        success, conversation, _user_message = gpt.conversation.add_conversation(gpt.current_user.id, f"Conversation {i}")
        if success:
            gpt.message.add_message(conversation.id, "assistant", f"Message for conversation {i}", "content", None, 'provider_fake_llm', constants.API_BACKEND_DEFAULT_MODEL, '')
    success, history, user_message = gpt.get_history(limit=3)
    if success:
        print("\nHistory:\n")
        for id, conversation in history.items():
            print(conversation['title'])
    assert success
    assert len(history) == 3


if __name__ == '__main__':
    test_api_backend_get_history()
