import pytest
import requests

class TestChatGPTAPI:
    @pytest.mark.skip(reason="API currently seems broken")
    def test_ask_message(self):
        # message = {
        #     "message": "Hello",
        #     "new_conversation": True
        # }
        url = "http://localhost:5000/conversations"

        prompt = "Hello, how are you?"

        # Create the request headers and body
        headers = {"Content-Type": "text/plain"}
        data = prompt.encode("utf-8")

        # Send the POST request to the API endpoint
        response = requests.post(url, headers=headers, data=data)
        print(response.status_code)
        print(response.content)
        assert response.status_code == 200
