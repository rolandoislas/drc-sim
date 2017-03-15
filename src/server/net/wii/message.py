from src.server.util.logging.logger_backend import LoggerBackend


class MessageHandler:
    def __init__(self):
        pass

    @staticmethod
    def update(packet):
        LoggerBackend.debug('MSG: ' + packet.encode('hex'))

    def close(self):
        pass
