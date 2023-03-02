import logging

class LogCapable:
    def __init__(
        self,
        console_level=logging.ERROR,
        console_format=logging.Formatter("%(levelname)s - %(message)s"),
        file_level=logging.DEBUG,
        file_format=logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"),
        debug_log=None
    ):
        self.console_level=console_level
        self.console_format=console_format
        self.file_level=file_level
        self.file_format=file_format

        self.log=logging.getLogger(self.__class__.__name__)
        self.log.setLevel(logging.DEBUG)

        console_handler=logging.StreamHandler()
        console_handler.setFormatter(console_format)
        console_handler.setLevel(console_level)
        self.log.addHandler(console_handler)

        if debug_log:
            file_handler=logging.FileHandler(debug_log)
            file_handler.setFormatter(file_format)
            file_handler.setLevel(file_level)
            self.log.addHandler(file_handler)
