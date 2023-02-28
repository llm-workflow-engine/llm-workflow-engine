import argparse

from flask import Flask, jsonify, request

from chatgpt_wrapper.chatgpt import ChatGPT


def create_application(name, headless: bool = True, browser="firefox", model="default", timeout=60, debug_log=None, proxy=None):
    app = Flask(name)
    chatgpt = ChatGPT(headless, browser, model, timeout, debug_log, proxy)

    def _error_handler(message):
        return jsonify({"success": False, "error": str(message)}), 500

    @app.route("/conversations", methods=["POST"])
    def ask():
        """
        Ask a question.

        Path:
            POST /conversations

        Request Body:
            STRING:
                Some text.

        Returns:
            STRING:
                Some response.
        """
        prompt = request.get_data().decode("utf-8")
        result = chatgpt.ask(prompt)
        return result

    @app.route("/conversations/new", methods=["POST"])
    def new_conversation():
        """
        Start a new conversation.

        Path:
            POST /conversations/new

        Returns:
            JSON:
                {
                    "success": true,
                }

            JSON:
                {
                    "success": false,
                    "error": "Failed to start new conversation"
                }
        """
        chatgpt.new_conversation()
        return jsonify({"success": True, "parent_message_id": chatgpt.parent_message_id})

    @app.route("/conversations/<string:conversation_id>", methods=["DELETE"])
    def delete_conversation(conversation_id):
        """
        Delete a conversation.

        Path:
            DELETE /conversations/:conversation_id

        Parameters:
            conversation_id (str): The ID of the conversation to delete.

        Returns:
            JSON:
                {
                    "success": true,
                }

            JSON:
                {
                    "success": false,
                    "error": "Failed to delete conversation"
                }
        """
        result = chatgpt.delete_conversation(conversation_id)
        if result:
            return jsonify(result)
        else:
            return _error_handler("Failed to delete conversation")

    @app.route("/conversations/<string:conversation_id>/set-title", methods=["PATCH"])
    def set_title(conversation_id):
        """
        Set the title of a conversation.

        Path:
            PATCH /conversations/:conversation_id/set-title

        Parameters:
            conversation_id (str): The ID of the conversation to set the title for.

        Request Body:
            JSON:
                {
                    "title": "New Title"
                }

        Returns:
            JSON:
                {
                    "success": true,
                }

            JSON:
                {
                    "success": false,
                    "error": "Failed to set title"
                }
        """
        json = request.get_json()
        title = json["title"]
        result = chatgpt.set_title(title, conversation_id=conversation_id)
        if result:
            return jsonify(result)
        else:
            return _error_handler("Failed to set title")

    @app.route("/history", methods=["GET"])
    def get_history():
        """
        Retrieve conversation history.

        Path:
            GET /history

        Query Parameters:
            limit (int, optional): The maximum number of conversations to return (default is 20).
            offset (int, optional): The number of conversations to skip before starting to return results (default is 0).

        Returns:
            JSON:
                {
                    ":conversation_id": {
                        "id": "abc123",
                        "title": "Conversation Title",
                        ...
                    },
                    ...
                }

            JSON:
                {
                    "error": "Failed to get history"
                }
        """
        limit = request.args.get("limit", 20)
        offset = request.args.get("offset", 0)
        result = chatgpt.get_history(limit=limit, offset=offset)
        if result:
            return jsonify(result)
        else:
            return _error_handler("Failed to get history")

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    app = create_application("chatgpt")
    app.run(host="0.0.0.0", port=args.port, threaded=False)
