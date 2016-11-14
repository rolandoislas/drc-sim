import socket

from src.common.net.codec import Codec
from src.common.net.net_util import NetUtil
from src.server.net import sockets
from src.server.net.server.command import ServiceCMD


class ServiceVID:
    __name__ = "ServiceVID"

    def __init__(self):
        pass

    def update(self, packet, address):
        self.check_register_command(packet, address)

    @staticmethod
    def check_register_command(packet, address):
        if ServiceCMD.parse_command("REGISTER", packet) != "0":
            sockets.Sockets.client_sockets[address] = ServiceVID

    @classmethod
    def broadcast(cls, packet):
        for sock in sockets.Sockets.client_sockets.keys():
            if sockets.Sockets.client_sockets[sock].__name__ == ServiceVID.__name__:
                try:
                    sock.sendall(Codec.encode(packet))
                except socket.error, e:
                    print e.strerror
                    del sockets.Sockets.client_sockets[sock]
