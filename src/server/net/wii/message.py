from src.server.data.args import Args


class MessageHandler:
    def __init__(self):
        pass

    @staticmethod
    def update(packet):
        if Args.args.debug:
            print 'MSG', packet.encode('hex')

    def close(self):
        pass
