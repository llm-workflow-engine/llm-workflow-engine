from lwe.core.tool import Tool


class ReverseContent(Tool):
    def __call__(self, content: str) -> dict:
        """
        Reverse the provided content

        :param content: The content to reverse.
        :type content: str
        :return: A dictionary containing the reversed content.
        :rtype: dict
        """
        try:
            reversed_content = content[::-1]
            output = {
                "result": reversed_content,
                "message": "Reversed the content string",
            }
        except Exception as e:
            output = {
                "error": str(e),
            }
        return output
