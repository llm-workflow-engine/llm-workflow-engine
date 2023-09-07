#!/usr/bin/env python

from lwe import ApiBackend


def test_api_backend_streaming(test_config):

    stream_response = ""

    def stream_callback(content):
        nonlocal stream_response
        stream_response += content

    # test_config.set('debug.log.enabled', True)
    backend = ApiBackend(test_config)
    response = ""
    request_overrides = {
        'stream_callback': stream_callback
    }
    success, response, _user_message = backend.ask_stream("Say three words about earth", request_overrides=request_overrides)

    assert success
    if success:
        print("\nRESPONSE:\n")
        print(response)
    assert isinstance(response, str)
    assert response == "test response"
    assert stream_response == response


if __name__ == '__main__':
    test_api_backend_streaming()
