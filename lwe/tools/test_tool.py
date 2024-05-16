from lwe.core.tool import Tool


class TestTool(Tool):
    # Ignore for pytest.
    __test__ = False

    def __call__(self, word: str, repeats: int, enclose_with: str = "") -> dict:
        """
        Repeat the provided word a number of times.

        :param word: The word to repeat.
        :type content: str
        :param repeats: The number of times to repeat the word.
        :type repeats: int
        :param enclose_with: Optional string to enclose the final content.
        :type enclose_with: str, optional
        :return: A dictionary containing the repeated content.
        :rtype: dict
        """
        try:
            repeated_content = " ".join([word] * repeats)
            enclosed_content = f"{enclose_with}{repeated_content}{enclose_with}"
            output = {
                "result": enclosed_content,
                "message": f"Repeated the word {word} {repeats} times.",
            }
        except Exception as e:
            output = {
                "error": str(e),
            }
        return output
