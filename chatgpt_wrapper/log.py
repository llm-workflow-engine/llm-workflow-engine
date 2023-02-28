import logging

class LogCapability:
    def __init__(
        self, debug_log,
        console_level=logging.ERROR,
        console_format=logging.Formatter("%(levelname)s - %(message)s"),
        file_level=logging.DEBUG,
        file_format=logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s")
    ):
        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(logging.DEBUG)
        log_console_handler = logging.StreamHandler()
        log_console_handler.setFormatter(console_format)
        log_console_handler.setLevel(console_level)
        logger.addHandler(log_console_handler)
        if debug_log:
            log_file_handler=logging.FileHandler(debug_log)
            log_file_handler.setFormatter(file_format)
            log_file_handler.setLevel(file_level)
            logger.addHandler(log_file_handler)
        self.log=logger
