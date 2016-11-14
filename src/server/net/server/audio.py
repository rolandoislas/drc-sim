import socket

from src.server.net import sockets
from src.server.net.server.command import ServiceCMD


class ServiceAUD:
    __name__ = "ServiceAUD"

    def __init__(self):
        pass

    def update(self, packet, address):
        self.check_register_command(packet, address)

    @staticmethod
    def check_register_command(packet, address):
        if ServiceCMD.parse_command("REGISTER", packet) != "0":
            sockets.Sockets.client_sockets[address] = ServiceAUD

    @classmethod
    def forward_packet(cls, packet):
        for address in sockets.Sockets.client_sockets.keys():
            if sockets.Sockets.client_sockets[address].__name__ == ServiceAUD.__name__:
                try:
                    sockets.Sockets.SERVER_AUD_S.sendto(packet, address)
                except socket.error:
                    del sockets.Sockets.client_sockets[address]
