import socket

import time

from src.common.net.codec import Codec
from src.server.net import sockets
from src.server.net.server.command import ServiceCMD


class ServiceAUD:
    __name__ = "ServiceAUD"

    def __init__(self):
        pass

    def update(self, packet, address):
        pass

    @classmethod
    def broadcast(cls, packet):
        for sock in sockets.Sockets.client_sockets.keys():
            if sockets.Sockets.client_sockets[sock].__name__ == ServiceAUD.__name__:
                try:
                    sock.sendall(Codec.encode(packet))
                except socket.error, e:
                    print e.strerror
                    del sockets.Sockets.client_sockets[sock]
