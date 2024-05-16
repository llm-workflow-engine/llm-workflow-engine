import re

from pydantic import BaseModel, Field
from typing import List

from lwe.core.tool import Tool


class Sentiment(BaseModel):
    name: str = Field(..., description="Single word sentiment description")


class Topic(BaseModel):
    name: str = Field(..., description="One or two word description of a topic")


class ExtractSentimentTopics(BaseModel):
    sentiments: List[Sentiment] = Field(..., description="One to three sentiment descriptions")
    topics: List[Topic] = Field(..., description="One to three topic descriptions")


class StoreSentimentAndTopics(Tool):
    def clean_results(self, results):
        return [re.sub(r"\W", "_", elem["name"].lower()) for elem in results]

    def get_config(self) -> dict:
        return {
            "name": "store_sentiment_and_topics",
            "description": "Store the extracted sentiments and topics",
            "parameters": ExtractSentimentTopics.schema(),
        }

    def __call__(self, sentiments: List[str], topics: List[str]) -> dict:
        """
        Store the extracted sentiments and topics

        :param content: The content to reverse.
        :type content: str
        :return: A dictionary containing the reversed content.
        :rtype: dict
        """
        try:
            output = {
                "sentiments": self.clean_results(sentiments),
                "topics": self.clean_results(topics),
                "message": "Stored the sentiments and topics",
            }
        except Exception as e:
            output = {
                "error": str(e),
            }
        return output
