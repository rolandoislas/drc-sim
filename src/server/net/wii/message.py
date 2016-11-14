class MessageHandler:
    def __init__(self):
        pass

    @staticmethod
    def update(packet):
        print 'MSG', packet.encode('hex')

    def close(self):
        pass
