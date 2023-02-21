class ChatGPTError(RuntimeError):
    pass

class RateLimitError(ChatGPTError):
    pass

class NetworkError(ChatGPTError):
    pass

class NotLoggedInError(ChatGPTError):
    pass

class ChatGPTResponseError(ChatGPTError):
    pass