import requests
from unittest import TestCase


class TestChatGPTAPI(TestCase):
    def test_ask_message(self):
        # message = {
        #     "message": "Hello",
        #     "new_conversation": True
        # }
        url = "http://localhost:5001/conversations"

        prompt = "Hello, how are you?"

        # Create the request headers and body
        headers = {"Content-Type": "text/plain"}
        data = prompt.encode("utf-8")

        # Send the POST request to the API endpoint
        response = requests.post(url, headers=headers, data=data)
        print(response.status_code)
        print(response.content)
        self.assertEqual(response.status_code, 200)
