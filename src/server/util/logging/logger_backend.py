from src.server.util.logging.logger import Logger


class LoggerBackend(Logger):
    def __init__(self, name=None):
        Logger.__init__(self, name)
        LoggerBackend.logger, LoggerBackend.console_handler, LoggerBackend.file_handler = self.create_logger(name)


LoggerBackend("backend")
