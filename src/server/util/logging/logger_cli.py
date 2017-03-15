from src.server.util.logging.logger import Logger


class LoggerCli(Logger):
    def __init__(self, name=None):
        Logger.__init__(self, name)
        LoggerCli.logger, LoggerCli.console_handler, LoggerCli.file_handler = self.create_logger(name)

LoggerCli("cli")
