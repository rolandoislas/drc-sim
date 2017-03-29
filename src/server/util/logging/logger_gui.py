from src.server.util.logging.logger import Logger


class LoggerGui(Logger):
    def __init__(self, name=None):
        Logger.__init__(self, name)
        LoggerGui.logger, LoggerGui.console_handler, LoggerGui.file_handler = self.create_logger(name)

LoggerGui("gui")
