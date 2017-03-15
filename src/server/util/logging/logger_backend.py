from src.server.util.logging.logger import Logger


class LoggerBackend(Logger):
    def __init__(self, name=None):
        Logger.__init__(self, name)


LoggerBackend("backend")
