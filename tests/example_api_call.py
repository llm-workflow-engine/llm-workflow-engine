import requests
import argparse


def test_ask_message(host, port):
    # message = {
    #     "message": "Hello",
    #     "new_conversation": True
    # }
    url = f"http://{host}:{port}/conversations"

    prompt = "Hello, how are you?"
    print(prompt)
    # Create the request headers and body
    headers = {"Content-Type": "text/plain"}
    data = prompt.encode("utf-8")

    # Send the POST request to the API endpoint
    response = requests.post(url, headers=headers, data=data)
    print(response.content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--host", type=str, default="localhost")
    args = parser.parse_args()
    test_ask_message(args.host, args.port)
