#!/usr/bin/env python

from ..base import (
    store_conversation_threads,
)

from lwe import ApiBackend
from lwe.core import constants


def test_api_backend_get_history(test_config):
    # test_config.set('debug.log.enabled', True)
    test_config.set('backend_options.default_user', 1)
    backend = ApiBackend(test_config)
    store_conversation_threads(backend, rounds=3)
    success, history, user_message = backend.get_history(limit=3)
    if success:
        print("\nHistory:\n")
        for id, conversation in history.items():
            print(conversation['title'])
    assert success
    assert len(history) == 3


if __name__ == '__main__':
    test_api_backend_get_history()
