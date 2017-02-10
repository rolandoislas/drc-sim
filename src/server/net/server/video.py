from src.server.net import sockets


class ServiceVID:
    __name__ = "ServiceVID"

    def __init__(self):
        pass

    def update(self, packet, address):
        pass

    @classmethod
    def broadcast(cls, packet):
        sockets.Sockets.broadcast_media_packet(packet, ServiceVID.__name__)
