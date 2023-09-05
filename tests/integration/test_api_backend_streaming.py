#!/usr/bin/env python

from lwe import ApiBackend


def test_api_backend_streaming(test_config):

    stream_response = ""
    def stream_callback(content):
        nonlocal stream_response
        stream_response += content

    # test_config.set('debug.log.enabled', True)
    gpt = ApiBackend(test_config)
    response = ""
    request_overrides = {
        'stream_callback': stream_callback
    }
    success, response, _user_message = gpt.ask_stream("Say three words about earth", request_overrides=request_overrides)

    assert success
    if success:
        print("\nRESPONSE:\n")
        print(response)
    assert isinstance(response, str)
    assert len(response) > 0
    assert len(stream_response) > 0


if __name__ == '__main__':
    test_api_backend_streaming()
