#!/usr/bin/env python

from lwe import ApiBackend


def test_api_backend_non_streaming(test_config):
    # test_config.set('debug.log.enabled', True)
    gpt = ApiBackend(test_config)
    success, response, _user_message = gpt.ask("Say hello!")
    if success:
        print("\nRESPONSE:\n")
        print(response)
    assert success
    assert isinstance(response, str)


if __name__ == '__main__':
    test_api_backend_non_streaming()
