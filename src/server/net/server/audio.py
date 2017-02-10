from src.server.net import sockets


class ServiceAUD:
    __name__ = "ServiceAUD"

    def __init__(self):
        pass

    def update(self, packet, address):
        pass

    @classmethod
    def broadcast(cls, packet):
        sockets.Sockets.broadcast_media_packet(packet, ServiceAUD.__name__)
