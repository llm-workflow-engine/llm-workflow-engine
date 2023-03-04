import logging
from .config import Config

c=Config()
console_level=c.get("log.console.level")
console_format=c.get("log.console.format")
file_level=c.get("debug.log.level")
file_format=c.get("debug.log.format")
debug_log_enabled=c.get("debug.log.enabled")
class LogCapable:
    def __init__(
        self,
        console_level=console_level,
        console_format=console_format,
        file_level=file_level,
        file_format=file_format,
        debug_log=debug_log_enabled
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
            debug_file_path=c.get("debug.log.filepath")
            file_handler=logging.FileHandler(debug_file_path)
            file_handler.setFormatter(file_format)
            file_handler.setLevel(file_level)
            self.log.addHandler(file_handler)
