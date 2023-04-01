import argparse

from flask import Flask, jsonify, request

from chatgpt_wrapper.backends.openai.api import OpenAIAPI
from chatgpt_wrapper.core.config import Config


def create_application(name, config=None, timeout=60, proxy=None):
    config = config or Config()
    config.set('debug.log.enabled', True)
    gpt = OpenAIAPI(config)
    app = Flask(name)

    def _error_handler(message, status_code=500):
        return jsonify({"success": False, "error": str(message)}), status_code

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
        success, result, user_message = gpt.ask(prompt)
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
        gpt.new_conversation()
        return jsonify({"success": True, "parent_message_id": gpt.parent_message_id})

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
        success, result, user_message = gpt.delete_conversation(conversation_id)
        if success:
            return user_message
        else:
            return _error_handler(user_message)

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
        success, conversation, user_message = gpt.set_title(title, conversation_id)
        if success:
            return jsonify(gpt.conversation.orm.object_as_dict(conversation))
        else:
            return _error_handler("Failed to set title")

    @app.route("/history/<int:user_id>", methods=["GET"])
    def get_history(user_id):
        """
        Retrieve conversation history for a user.

        Path:
            GET /history/:user_id

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
        success, result, user_message = gpt.get_history(limit=limit, offset=offset, user_id=user_id)
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
