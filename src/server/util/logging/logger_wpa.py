from src.server.util.logging.logger import Logger


class LoggerWpa(Logger):
    def __init__(self, name=None):
        Logger.__init__(self, name)
        LoggerWpa.logger, LoggerWpa.console_handler, LoggerWpa.file_handler = self.create_logger(name)

LoggerWpa("wpa")
